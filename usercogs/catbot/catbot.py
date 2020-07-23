import discord
import asyncio
import random
import aiohttp
import os
from discord.ext import commands
from utils.storage import RedisCollection
from utils import checks

cattriggers = [
    'cat me',
    'meow me',
    'give me a cat'
]

dogtriggers = [
    'give me a dog',
    'dog me',
    'bork me',
    'woof me'
]

class FetchFailed(Exception):
    pass

class CatBot(commands.Cog):

    def __init__(self, heleus):
        self.heleus = heleus
        self.db = RedisCollection(heleus.redis, 'settings')
        self.haste_url = os.environ.get('HELEUS_HASTE_URL', 'https://hastebin.com')
        self.help_group = 'General'
        self.help_image = 'https://i.imgur.com/ybGMt1k.png'
        self.invite_url = discord.utils.oauth_url(self.heleus.user.id)

        for obj in dir(self):  # docstring formatting
            if obj.startswith('_'):
                continue
            obj = getattr(self, obj)
            if not isinstance(obj, commands.Command):
                continue
            if not obj.help:
                continue
            obj.help = obj.help.format(self.heleus.name, self.heleus.command_prefix[0])
    
    async def fetch_settings(self, ctx):
        if ctx.channel.type == discord.ChannelType.text:
            return await self.db.get(
                ctx.guild.id,
                {
                    'cattriggers': cattriggers,
                    'dogtriggers': dogtriggers,
                    'require_mention': True
                }
            )
        else:
            # Should only be for DMs
            return {
                'cattriggers': cattriggers,
                'dogtriggers': dogtriggers,
                'require_mention': False
            }
    
    def format_list(self, l: list, limit=768):
        if l:
            chars = 0
            final = []
            remainder = len(l)
            for item in l:
                length = len(item) + 2
                if (chars + length) <= limit:
                    chars += length
                    final.append(item)
                    remainder -= 1
                else:
                    if final:
                        return ', '.join(final), remainder
                    else:
                        return '', remainder
            return ', '.join(final), 0
        return '', 0
    
    @commands.command(name='import')
    @checks.is_owner()
    async def _import(self, ctx, url):
        """Import settings from the old version of Cat Bot."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json(encoding='utf-8', content_type='text/plain')
        for k, info in data.items():
            converted = {}
            converted['cattriggers'] = cattriggers
            converted['dogtriggers'] = dogtriggers
            if info['keywordtrigger']:
                converted['require_mention'] = False
            else:
                converted['require_mention'] = True
            await self.db.set(int(k), converted)
        await ctx.send('Done.')

    @commands.command()
    async def invite(self, ctx):
        """Returns Cat Bot's invite link for inviting to your own server."""
        await ctx.send(f'🐱You can invite me to your server using the following url:\n{self.invite_url}'
                       '\n\nYou will need the **Manage Server** permission to add me to a server. '
                       f'Run `{self.heleus.command_prefix[0]}help` to see what you can customise!')
    
    @commands.command()
    async def phrases(self, ctx):
        """List all available phrases on the server."""
        settings = await self.fetch_settings(ctx)
        cats, cats_remain = self.format_list(settings['cattriggers'])
        dogs, dogs_remain = self.format_list(settings['dogtriggers'])

        if not cats and not dogs:
            return await ctx.send(f'😿 I have no phrases to respond to on **{ctx.guild.name}**!')

        if ctx.channel.type == discord.ChannelType.text:
            message = f'🐱 Here are the phrases used to summon me on **{ctx.guild.name}**:\n'
        else:
            message = f'🐱 Here are the phrases used to summon me in DMs:\n'

        if cats:
            message += f'\nCats: **{cats}**'
            if cats_remain:
                message += f' and **{cats_remain}** more...'
        if not cats and cats_remain:
            message += f'\nCats: **{cats_remain}** phrase{"s" if cats_remain != 1 else ""} that {"are" if cats_remain != 1 else "is"} too long to fit here!'
        
        if dogs:
            message += f'\nDogs: **{dogs}**'
            if dogs_remain:
                message += f' and **{dogs_remain}** more...'
        if not dogs and dogs_remain:
            message += f'\nDogs: **{dogs_remain}** phrase{"s" if dogs_remain != 1 else ""} that {"are" if dogs_remain != 1 else "is"} too long to fit here!'
        
        if settings['require_mention']:
            message += f'\n\nYou need to @mention me for me to respond on **{ctx.guild.name}**!'
        await ctx.send(message)
    
    @commands.group(name='phrase', invoke_without_command=True)
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def phrase(self, ctx):
        """Manage custom phrases for {0} to respond to on your server."""
        await self.heleus.send_command_help(ctx)

    @phrase.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def add(self, ctx, type: str, *, phrase: str):
        """Add a custom phrase for {0} to respond to.

        Arguments
        ---------
         `type` - The type of animal to respond with, either `cat` or `dog`
         `phrase` - The custom phrase for {0} to respond to
         
        Example
        -------
        `{1}phrase add cat kitty time`"""
        type = type.lower()
        if type not in ['cat', 'dog']:
            return await self.heleus.send_command_help(ctx)
        phrase = phrase.lower()
        settings = await self.fetch_settings(ctx)
        if type == 'cat':
            if len(settings['dogtriggers']) >= 50:
                return await ctx.send('😿 You have too many cat phrases!')
            if phrase in settings['cattriggers']:
                return await ctx.send('😿 That phrase already exists!')
            settings['cattriggers'].append(phrase)
        elif type == 'dog':
            if len(settings['dogtriggers']) >= 50:
                return await ctx.send('🐶 You have too many dog phrases!')
            if phrase in settings['dogtriggers']:
                return await ctx.send('🐶 That phrase already exists!')
            settings['dogtriggers'].append(phrase)
        await self.db.set(ctx.guild.id, settings)
        await ctx.send(f'{"🐱" if type == "cat" else "🐶"} Phrase added!')
    
    @phrase.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def remove(self, ctx, type: str, *, phrase: str):
        """Remove a custom phrase for {0} to respond to.

        Arguments
        ---------
        `type` - The type of animal to respond with, either `cat` or `dog`
        `phrase` - The custom phrase for {0} to respond to
         
        Example
        -------
        `{1}phrase remove cat kitty time`"""
        type = type.lower()
        if type not in ['cat', 'dog']:
            return await self.heleus.send_command_help(ctx)
        phrase = phrase.lower()
        settings = await self.fetch_settings(ctx)
        if type == 'cat':
            if phrase not in settings['cattriggers']:
                return await ctx.send('😿 That phrase doesn\'t exist! Check your spelling and try again.')
            settings['cattriggers'].remove(phrase)
        elif type == 'dog':
            if phrase not in settings['dogtriggers']:
                return await ctx.send('🐶 That phrase doesn\'t exist! Check your spelling and try again.')
            settings['dogtriggers'].remove(phrase)
        await self.db.set(ctx.guild.id, settings)
        await ctx.send(f'{"🐱" if type == "cat" else "🐶"} Phrase removed!')
    
    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def mention(self, ctx):
        """Toggle if mentioning {0} is required for them to respond to messages."""
        settings = await self.fetch_settings(ctx)
        if settings['require_mention']:
            settings['require_mention'] = False
            await ctx.send('🐱 Okay, I no longer need to be @mentioned for me to respond to messages!')
        else:
            settings['require_mention'] = True
            await ctx.send('🐱 Okay, I will now only respond to messages if they @mention me!')
        await self.db.set(ctx.guild.id, settings)
    
    @commands.command()
    @checks.is_owner()
    async def block(self, ctx, *, url):
        """Block a URL from being posted by {0}."""
        blocked = await self.db.get('blocked', [])
        if url in blocked:
            return await ctx.send('😾 That image is already blocked.')
        blocked.append(url)
        await self.db.set('blocked', blocked)
        await ctx.send('😾 That image will not be posted again.')
    
    @commands.command()
    @checks.is_owner()
    async def unblock(self, ctx, *, url):
        """Unblocks a URL from being posted by {0}."""
        blocked = await self.db.get('blocked', [])
        if url not in blocked:
            return await ctx.send('😾 That image isn\'t blocked.')
        blocked.remove(url)
        await self.db.set('blocked', blocked)
        await ctx.send('🐱 That image has been unblocked.')
    
    @commands.command()
    @checks.is_owner()
    async def blocklist(self, ctx):
        """Returns a paste containing all the blocked URLs."""
        blocked = await self.db.get('blocked', [])
        if not blocked:
            return await ctx.send('🐱 There are no blocked images.')
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{self.haste_url}/documents', data='\n'.join(blocked)) as resp:
                return await ctx.send(f'🐱 Here is a list of blocked images\n\n{self.haste_url}/{resp["key"]}.txt')

    async def fetch_cat_pic(self, tries=5):
        blocked = await self.db.get('blocked', [])
        async with aiohttp.ClientSession() as session:
            for i in range(tries):
                async with session.get("https://api.thecatapi.com/v1/images/search") as resp:
                    if resp.status != 200:
                        await asyncio.sleep(0.2)
                        continue
                    data = await resp.json(encoding='utf-8')
                    image = data[0]['url']
                    if image in blocked:
                        continue
                    return image
        raise FetchFailed
    
    async def fetch_dog_pic(self, tries=5):
        blocked = await self.db.get('blocked', [])
        async with aiohttp.ClientSession() as session:
            for i in range(tries):
                async with session.get("https://dog.ceo/api/breeds/image/random") as resp:
                    if resp.status != 200:
                        await asyncio.sleep(0.2)
                        continue
                    data = await resp.json(encoding='utf-8')
                    image = data['message']
                    if image in blocked:
                        continue
                    return image
        raise FetchFailed

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.heleus.user:
            return
        if message.author.bot:
            return
        if message.author.public_flags.system:
            return
        if message.flags.is_crossposted:

            return
        
        settings = await self.fetch_settings(message)
        if settings['require_mention'] and not self.heleus.user in message.mentions:
            return
        
        if message.guild:
            if not message.channel.permissions_for(message.guild.me).send_messages:
                return
            if not message.channel.permissions_for(message.guild.me).embed_links:
                return await message.channel.send(f'😿 I\'m not allowed to send images in here!')
        
        cat = False
        dog = False
        for phrase in settings['cattriggers']:
            if phrase in message.content.lower():
                cat = True
                break
        for phrase in settings['dogtriggers']:
            if phrase in message.content.lower():
                dog = True
                break
        if cat and dog:
            pick = random.choice(['cat', 'dog'])
            if pick == 'cat':
                dog = False
            else:
                cat = False
        elif not cat and not dog:
            return
        await message.channel.trigger_typing()
        try:
            if cat:
                image = await self.fetch_cat_pic()
            else:
                image = await self.fetch_dog_pic()
        except FetchFailed:
            return await message.channel.send(f'{"😿" if cat else "🐶"} I was unable to find you a {"cat" if cat else "dog"}!')
        
        embed = discord.Embed()
        if message.guild:
            embed.colour = message.guild.me.colour
        embed.set_author(
            name=f'{"🐱Cat" if cat else "🐶Dog"} for {message.author.name}',
            url=image
        )
        embed.set_image(url=image)

        await message.channel.send(embed=embed)

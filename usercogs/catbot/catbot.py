import discord
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

class CatBot(commands.Cog):

    def __init__(self, heleus):
        self.heleus = heleus
        self.db = RedisCollection(heleus.redis, 'settings')

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
                return await ctx.send('😿 You have too many dog phrases!')
            if phrase in settings['dogtriggers']:
                return await ctx.send('😿 That phrase already exists!')
            settings['dogtriggers'].append(phrase)
        await self.db.set(ctx.guild.id, settings)
        await ctx.send('🐱 Phrase added!')
    
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
                return await ctx.send('😿 That phrase doesn\'t exist! Check your spelling and try again.')
            settings['dogtriggers'].remove(phrase)
        await self.db.set(ctx.guild.id, settings)
        await ctx.send('🐱 Phrase removed!')
    

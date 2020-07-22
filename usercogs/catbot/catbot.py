import discord
from discord.ext import commands
from utils.storage import RedisCollection

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
                if chars + length >= limit:
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
        settings = await self.fetch_settings(ctx)
        cats, cats_remain = self.format_list(settings['cattriggers'])
        dogs, dogs_remain = self.format_list(settings['dogtriggers'])

        if not cats and not dogs:
            return await ctx.send(f'🐱 I have no phrases to respond to on **{ctx.guild.name}**!')

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
            message += f'\n\nYou need to @mention me for me to respond on {ctx.guild.name}!'
        await ctx.send(message)
        
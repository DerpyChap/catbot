from .catbot import CatBot

def setup(heleus):
    heleus.add_cog(CatBot(heleus))
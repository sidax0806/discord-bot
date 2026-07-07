import discord
from discord.ext import commands
from discord import app_commands

import data.tournament_data as tournament_data


GUILD_ID = 1238127187648057466


class Ranking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


async def setup(bot):
    await bot.add_cog(Ranking(bot))

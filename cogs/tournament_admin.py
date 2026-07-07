import discord
from discord.ext import commands
from discord import app_commands

from database.tournament_repo import list_tournaments, load_tournament_by_id, delete_tournament
from database.player_repo import load_players
from database.match_repo import load_matches
import data.tournament_data as tournament_data


GUILD_ID = 1238127187648057466


class TournamentAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


async def setup(bot):
    await bot.add_cog(TournamentAdmin(bot))

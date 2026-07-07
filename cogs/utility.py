import discord
from discord.ext import commands
from discord import app_commands

import data.tournament_data as tournament_data


GUILD_ID = 1238127187648057466


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==========================
    # 大会終了
    # ==========================
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="大会終了", description="大会を終了します")
    async def end_tournament(self, interaction: discord.Interaction):
        t = tournament_data.current_tournament

        if t is None:
            await interaction.response.send_message("❌ 終了する大会がありません。", ephemeral=True)
            return

        t["started"] = False
        tournament_data.save_all()

        embed = discord.Embed(
            title="🏁 大会終了",
            description=f"大会 **{t['name']}** を終了しました。",
            color=discord.Color.red()
        )

        await interaction.response.send_message(embed=embed)
        tournament_data.reset()


async def setup(bot):
    await bot.add_cog(Utility(bot))

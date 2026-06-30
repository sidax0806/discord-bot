import discord
from discord.ext import commands
from discord import app_commands

import data.tournament_data as tournament_data


GUILD_ID = 1238127187648057466


class Ranking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==========================
    # 順位表示
    # ==========================
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(
        name="順位",
        description="現在の順位を表示します"
    )
    async def ranking(self, interaction: discord.Interaction):

        t = tournament_data.current_tournament

        if t is None:
            await interaction.response.send_message("❌ 大会がありません。", ephemeral=True)
            return

        players = tournament_data.sort_players()

        if len(players) == 0:
            await interaction.response.send_message("参加者がいません。")
            return

        text = ""

        for i, p in enumerate(players, start=1):
            text += (
                f"**{i}位**  {p['name']}\n"
                f"　勝点：{p['match_points']} / "
                f"W-D-L：{p['wins']}-{p['draws']}-{p['losses']} / "
                f"OMW%：{p['omw']}\n\n"
            )

        embed = discord.Embed(
            title=f"📊 順位 - {t['name']}",
            color=discord.Color.gold()
        )

        embed.add_field(name="ランキング", value=text, inline=False)

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Ranking(bot))

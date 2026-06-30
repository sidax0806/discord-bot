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

    # ==========================
    # 大会一覧
    # ==========================
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="大会一覧", description="過去大会の一覧を表示します")
    async def list_t(self, interaction: discord.Interaction):

        tournaments = list_tournaments()

        if len(tournaments) == 0:
            await interaction.response.send_message("大会履歴はありません。")
            return

        text = ""
        for t in tournaments:
            status = "進行中" if t["started"] else "終了"
            text += f"ID: {t['id']} / {t['name']} / R{t['round']} / {status}\n"

        embed = discord.Embed(
            title="📚 大会一覧",
            description=text,
            color=discord.Color.blue()
        )

        await interaction.response.send_message(embed=embed)

    # ==========================
    # 大会復元
    # ==========================
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="大会復元", description="指定した大会を復元します")
    @app_commands.describe(tournament_id="大会ID")
    async def restore(self, interaction: discord.Interaction, tournament_id: int):

        t = load_tournament_by_id(tournament_id)
        if t is None:
            await interaction.response.send_message("❌ 大会が見つかりません。", ephemeral=True)
            return

        # プレイヤー復元
        players = load_players(tournament_id)
        t["participants"] = players

        # 試合復元
        matches_raw = load_matches(tournament_id, t["round"])
        matches = []

        for m in matches_raw:
            p1 = next(p for p in players if p["id"] == m["player1_id"])
            p2 = next(p for p in players if p["id"] == m["player2_id"])

            matches.append({
                "table": m["table"],
                "player1": p1,
                "player2": p2,
                "winner": m["winner"],
                "finished": m["finished"]
            })

        t["matches"] = matches

        tournament_data.current_tournament = t

        embed = discord.Embed(
            title="♻️ 大会復元",
            description=f"大会 **{t['name']}** を復元しました。",
            color=discord.Color.green()
        )

        await interaction.response.send_message(embed=embed)

    # ==========================
    # 大会削除
    # ==========================
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="大会削除", description="大会履歴を削除します")
    @app_commands.describe(tournament_id="大会ID")
    async def delete(self, interaction: discord.Interaction, tournament_id: int):

        delete_tournament(tournament_id)

        embed = discord.Embed(
            title="🗑 大会削除",
            description=f"大会ID **{tournament_id}** を削除しました。",
            color=discord.Color.red()
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(TournamentAdmin(bot))

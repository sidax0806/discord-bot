import discord
from discord.ext import commands
from discord import app_commands

import data.tournament_data as tournament_data
from database.tournament_repo import delete_tournament


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

        # 保存して終了扱いにする
        t["started"] = False
        tournament_data.save_all()

        embed = discord.Embed(
            title="🏁 大会終了",
            description=f"大会 **{t['name']}** を終了しました。",
            color=discord.Color.red()
        )

        await interaction.response.send_message(embed=embed)

        # メモリ上の大会データを消す
        tournament_data.reset()

    # ==========================
    # 大会情報
    # ==========================
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="大会情報", description="現在の大会情報を表示します")
    async def info(self, interaction: discord.Interaction):

        t = tournament_data.current_tournament

        if t is None:
            await interaction.response.send_message("❌ 現在進行中の大会はありません。", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📘 大会情報 - {t['name']}",
            color=discord.Color.blue()
        )

        embed.add_field(name="大会名", value=t["name"], inline=False)
        embed.add_field(name="ラウンド", value=str(t["round"]), inline=True)
        embed.add_field(
            name="状態",
            value="進行中" if t["started"] else "終了",
            inline=True
        )
        embed.add_field(
            name="参加人数",
            value=f"{len(t['participants'])}人",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    # ==========================
    # プレイヤー情報
    # ==========================
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="プレイヤー情報", description="指定プレイヤーの情報を表示します")
    @app_commands.describe(player="プレイヤーを選択")
    async def player_info(self, interaction: discord.Interaction, player: discord.Member):

        t = tournament_data.current_tournament

        if t is None:
            await interaction.response.send_message("❌ 大会がありません。", ephemeral=True)
            return

        p = tournament_data.get_player(player.id)

        if p is None:
            await interaction.response.send_message("❌ このプレイヤーは参加していません。", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"👤 プレイヤー情報 - {p['name']}",
            color=discord.Color.green()
        )

        embed.add_field(name="名前", value=p["name"], inline=False)
        embed.add_field(name="勝点", value=str(p["match_points"]), inline=True)
        embed.add_field(
            name="戦績",
            value=f"{p['wins']}勝 {p['draws']}分 {p['losses']}敗",
            inline=True
        )
        embed.add_field(
            name="ゲーム勝敗",
            value=f"{p['game_wins']} - {p['game_losses']}",
            inline=True
        )
        embed.add_field(name="OMW%", value=str(p["omw"]), inline=True)
        embed.add_field(name="OGW%", value=str(p["ogw"]), inline=True)
        embed.add_field(
            name="対戦相手数",
            value=str(len(p["opponents"])),
            inline=True
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Utility(bot))

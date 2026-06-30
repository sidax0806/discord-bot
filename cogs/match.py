import discord
from discord.ext import commands
from discord import app_commands

import data.tournament_data as tournament_data


GUILD_ID = 1238127187648057466


# ==========================
# モーダル用：試合結果処理（BO3対応）
# ==========================
async def process_result_modal(interaction: discord.Interaction, table: int, p1_games: int, p2_games: int, winner_name: str):

    t = tournament_data.current_tournament
    if t is None:
        await interaction.response.send_message("❌ 大会がありません。", ephemeral=True)
        return

    match = tournament_data.get_match(table)
    if match is None:
        await interaction.response.send_message("❌ その卓は存在しません。", ephemeral=True)
        return

    if match["finished"]:
        await interaction.response.send_message("⚠️ この試合は既に終了しています。", ephemeral=True)
        return

    p1 = match["player1"]
    p2 = match["player2"]

    # ==========================
    # 引き分け
    # ==========================
    if winner_name.lower() == "draw":
        p1["draws"] += 1
        p2["draws"] += 1

        p1["match_points"] += 1
        p2["match_points"] += 1

        match["winner"] = None
        match["finished"] = True

    else:
        # ==========================
        # BO3 ゲーム数記録
        # ==========================
        p1["game_wins"] += int(p1_games)
        p1["game_losses"] += int(p2_games)

        p2["game_wins"] += int(p2_games)
        p2["game_losses"] += int(p1_games)

        # ==========================
        # 勝者判定
        # ==========================
        if winner_name == p1["name"]:
            p1["wins"] += 1
            p2["losses"] += 1
            p1["match_points"] += 3
            match["winner"] = p1["id"]

        elif winner_name == p2["name"]:
            p2["wins"] += 1
            p1["losses"] += 1
            p2["match_points"] += 3
            match["winner"] = p2["id"]

        else:
            await interaction.response.send_message("❌ 勝者名が対戦者と一致しません。", ephemeral=True)
            return

        match["finished"] = True

    # ==========================
    # 対戦履歴追加
    # ==========================
    p1["opponents"].append(p2["id"])
    p2["opponents"].append(p1["id"])

    # ==========================
    # OMW% / OGW% 更新
    # ==========================
    tournament_data.update_omw(t)
    tournament_data.update_ogw(t)

    # ==========================
    # 結果表示
    # ==========================
    embed = discord.Embed(
        title="📊 結果登録（BO3）",
        color=discord.Color.green()
    )

    if winner_name.lower() == "draw":
        embed.add_field(
            name=f"第{table}卓",
            value=f"{p1['name']} 🤝 {p2['name']}（引き分け）",
            inline=False
        )
    else:
        embed.add_field(
            name=f"第{table}卓",
            value=f"勝者：**{winner_name}**\n"
                  f"ゲーム：{p1_games} - {p2_games}",
            inline=False
        )

    await interaction.response.send_message(embed=embed)


# ==========================
# スラッシュコマンド版（既存）
# ==========================
class Match(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(
        name="結果",
        description="試合結果を登録します（BO1/BO3対応）"
    )
    @app_commands.describe(
        table="卓番号",
        winner="勝者（引き分けの場合は誰でもOK）",
        p1_games="player1 のゲーム勝利数（BO3用）",
        p2_games="player2 のゲーム勝利数（BO3用）",
        draw="引き分けなら true"
    )
    async def result(
        self,
        interaction: discord.Interaction,
        table: int,
        winner: discord.Member,
        p1_games: int = 0,
        p2_games: int = 0,
        draw: bool = False
    ):

        t = tournament_data.current_tournament

        if t is None:
            await interaction.response.send_message("❌ 大会がありません。", ephemeral=True)
            return

        match = tournament_data.get_match(table)

        if match is None:
            await interaction.response.send_message("❌ その卓は存在しません。", ephemeral=True)
            return

        if match["finished"]:
            await interaction.response.send_message("⚠️ この試合は既に終了しています。", ephemeral=True)
            return

        p1 = match["player1"]
        p2 = match["player2"]

        # ==========================
        # 引き分け
        # ==========================
        if draw:
            p1["draws"] += 1
            p2["draws"] += 1

            p1["match_points"] += 1
            p2["match_points"] += 1

            match["winner"] = None
            match["finished"] = True

        else:
            # ==========================
            # BO3 ゲーム数記録
            # ==========================
            p1["game_wins"] += p1_games
            p1["game_losses"] += p2_games

            p2["game_wins"] += p2_games
            p2["game_losses"] += p1_games

            # ==========================
            # マッチ勝敗処理
            # ==========================
            if winner.id == p1["id"]:
                p1["wins"] += 1
                p2["losses"] += 1

                p1["match_points"] += 3

                match["winner"] = p1["id"]

            elif winner.id == p2["id"]:
                p2["wins"] += 1
                p1["losses"] += 1

                p2["match_points"] += 3

                match["winner"] = p2["id"]

            else:
                await interaction.response.send_message("❌ 勝者が対戦者ではありません。", ephemeral=True)
                return

            match["finished"] = True

        # ==========================
        # 対戦履歴追加
        # ==========================
        p1["opponents"].append(p2["id"])
        p2["opponents"].append(p1["id"])

        # ==========================
        # OMW% / OGW% 更新
        # ==========================
        tournament_data.update_omw(t)
        tournament_data.update_ogw(t)

        # ==========================
        # 結果表示
        # ==========================
        embed = discord.Embed(
            title="📊 結果登録（BO3）",
            color=discord.Color.green()
        )

        if draw:
            embed.add_field(
                name=f"第{table}卓",
                value=f"{p1['name']} 🤝 {p2['name']}（引き分け）",
                inline=False
            )
        else:
            embed.add_field(
                name=f"第{table}卓",
                value=f"勝者：**{winner.display_name}**\n"
                      f"ゲーム：{p1_games} - {p2_games}",
                inline=False
            )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Match(bot))

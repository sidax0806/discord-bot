import discord
from discord.ext import commands
from discord import app_commands

import data.tournament_data as tournament_data


GUILD_ID = 1238127187648057466


async def send_round_notifications(interaction: discord.Interaction, round_num: int, matches: list, bye_player=None):
    t = tournament_data.current_tournament
    if t is None:
        return

    failed_users = []

    for p in t["participants"]:
        player_id = p["id"]
        print(f"[DM] attempting to send round notification to {p['name']} ({player_id})")
        try:
            user = await interaction.client.fetch_user(player_id)
            print(f"[DM] fetched user object for {p['name']}: {user}")
        except (discord.NotFound, discord.HTTPException) as exc:
            print(f"[DM] fetch_user failed for {p['name']}: {exc}")
            failed_users.append((p["name"], str(exc)))
            continue

        my_match = None
        for m in matches:
            if m["player1"]["id"] == player_id or m["player2"]["id"] == player_id:
                my_match = m
                break

        if my_match is None:
            if bye_player and bye_player["id"] == player_id:
                message = f"【{t['name']}】\nラウンド{round_num}はBYEです。勝点+3です。"
            else:
                continue
        else:
            opponent = my_match["player2"] if my_match["player1"]["id"] == player_id else my_match["player1"]
            message = (
                f"【{t['name']}】\n"
                f"ラウンド{round_num}の対戦相手です。\n"
                f"対戦相手: {opponent['name']}\n"
                f"卓: 第{my_match['table']}卓\n"
                f"形式: {t.get('bo', 'BO1')}"
            )

        try:
            await user.send(message)
            print(f"[DM] sent to {p['name']} ({player_id})")
        except discord.Forbidden as exc:
            print(f"[DM] forbidden for {p['name']}: {exc}")
            failed_users.append((p["name"], "DMの受信設定で送信できませんでした"))
        except discord.HTTPException as exc:
            print(f"[DM] http exception for {p['name']}: {exc}")
            failed_users.append((p["name"], str(exc)))

    if failed_users and hasattr(interaction, "channel") and interaction.channel is not None:
        names = ", ".join(name for name, _ in failed_users)
        try:
            await interaction.channel.send(
                f"⚠️ 次の参加者にはDMを送れませんでした: {names}\n"
                "Discordの『サーバーメンバーからのDMを許可』設定をご確認ください。"
            )
        except discord.HTTPException:
            pass


# ==========================
# モーダル用：試合結果処理（BO3対応）
# ==========================
async def process_result_modal(interaction: discord.Interaction, table: int, p1_games: int, p2_games: int, winner_name: str):

    print(f"[Match] process_result_modal called for table {table} by {winner_name}")
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
    await auto_next_round(interaction)

class Match(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


async def setup(bot):
    await bot.add_cog(Match(bot))

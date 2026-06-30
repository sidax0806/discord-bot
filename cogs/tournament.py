import random

import discord
from discord.ext import commands
from discord import app_commands

import data.tournament_data as tournament_data
from utils.swiss import swiss_pairing


GUILD_ID = 1238127187648057466


# ==========================
# ラウンドごとの順位表送信（固定メッセージ上書き版）
# ==========================
async def send_ranking_summary(interaction: discord.Interaction):
    t = tournament_data.current_tournament
    if t is None:
        return

    ranking = tournament_data.sort_players()

    # 勝ち点＋勝敗（W-L-D）
    text = "\n".join([
        f"{i+1}. {p['name']} - {p['match_points']}点 "
        f"({p['wins']}-{p['losses']}-{p['draws']})"
        for i, p in enumerate(ranking)
    ])

    embed = discord.Embed(
        title=f"📊 ラウンド{t['round']} 結果まとめ",
        color=discord.Color.blue()
    )
    embed.add_field(name="順位表（勝ち点＋勝敗）", value=text, inline=False)

    view = EndTournamentView(t["creator_id"])

    # すでに順位表メッセージがある → 上書き
    if "ranking_message" in t and t["ranking_message"] is not None:
        try:
            msg = await interaction.channel.fetch_message(t["ranking_message"])
            await msg.edit(embed=embed, view=view)
            return
        except:
            pass  # 取得できなければ新規送信に切り替え

    # 初回 → 新規送信して message_id を保存
    msg = await interaction.followup.send(embed=embed, view=view)
    t["ranking_message"] = msg.id



# ==========================
# ボタン無効化
# ==========================
async def disable_buttons(interaction: discord.Interaction):
    t = tournament_data.current_tournament
    if t is None:
        return

    view = JoinLeaveStartView(t["creator_id"])

    for item in view.children:
        item.disabled = True

    await interaction.message.edit(view=view)


# ==========================
# 大会終了処理
# ==========================
async def end_tournament_internal(interaction: discord.Interaction):
    t = tournament_data.current_tournament
    if t is None:
        await interaction.followup.send("❌ 大会がありません。")
        return

    embed = discord.Embed(
        title="🏁 大会終了",
        description=f"大会 **{t['name']}** を終了しました。",
        color=discord.Color.red()
    )

    await interaction.followup.send(embed=embed)
    tournament_data.reset()


# ==========================
# 総当たり終了判定
# ==========================
def is_round_robin_finished(t):
    participants = t["participants"]
    N = len(participants)

    # 全員が N-1 人と対戦していたら総当たり終了
    return all(len(p["opponents"]) >= N - 1 for p in participants)


# ==========================
# 自動ラウンド移行
# ==========================
async def auto_next_round(interaction: discord.Interaction):
    t = tournament_data.current_tournament
    if t is None:
        return

    if not tournament_data.all_matches_finished():
        return

    # 🔥 総当たり終了判定
    if is_round_robin_finished(t):
        await interaction.followup.send("🏁 総当たりが終了しました！大会を終了します。")
        await end_tournament_internal(interaction)
        return

    # 次ラウンドへ
    t["round"] += 1
    round_num = t["round"]

    for p in t["participants"]:
        p["bye"] = False

    matches_raw, bye_player = swiss_pairing(t)

    matches = []
    table = 1

    for m in matches_raw:
        matches.append({
            "table": table,
            "player1": m["player1"],
            "player2": m["player2"],
            "winner": None,
            "finished": False
        })
        table += 1

    t["matches"] = matches

    for m in matches:
        embed = discord.Embed(
            title=f"第{m['table']}卓（ラウンド{round_num}）",
            description=f"{m['player1']['name']} VS {m['player2']['name']}",
            color=discord.Color.blue()
        )
        view = ResultButtonView(m["table"])
        await interaction.followup.send(embed=embed, view=view)

    if bye_player:
        await interaction.followup.send(f"BYE: {bye_player['name']}（勝点 +3）")

    await send_ranking_summary(interaction)


# ==========================
# 大会開始処理
# ==========================
async def start_tournament_internal(interaction: discord.Interaction):
    t = tournament_data.current_tournament
    if t is None:
        await interaction.followup.send("❌ 大会がありません。")
        return

    participants = t["participants"]

    if len(participants) < 2:
        await interaction.followup.send("❌ 2人以上必要です。")
        return

    for p in participants:
        p["bye"] = False

    random.shuffle(participants)

    matches = []
    table = 1
    i = 0

    while i < len(participants):
        if i == len(participants) - 1:
            participants[i]["bye"] = True
            participants[i]["match_points"] += 3
            break

        matches.append({
            "table": table,
            "player1": participants[i],
            "player2": participants[i + 1],
            "winner": None,
            "finished": False
        })

        table += 1
        i += 2

    t["matches"] = matches
    t["started"] = True
    t["round"] = 1

    await disable_buttons(interaction)

    for m in matches:
        embed = discord.Embed(
            title=f"第{m['table']}卓",
            description=f"{m['player1']['name']} VS {m['player2']['name']}",
            color=discord.Color.green()
        )
        view = ResultButtonView(m["table"])
        await interaction.followup.send(embed=embed, view=view)

    bye_players = [p for p in participants if p.get("bye")]
    if bye_players:
        await interaction.followup.send(f"BYE: {bye_players[0]['name']}（勝点 +3）")

    await send_ranking_summary(interaction)


# ==========================
# 結果入力モーダル（BO1/BO3対応）
# ==========================
class ResultModal(discord.ui.Modal, title="試合結果入力"):
    p1_games = discord.ui.TextInput(label="Player1 ゲーム勝利数", default="0")
    p2_games = discord.ui.TextInput(label="Player2 ゲーム勝利数", default="0")
    winner = discord.ui.TextInput(label="勝者の名前（引き分けなら draw）", default="draw")

    def __init__(self, table: int):
        super().__init__()
        self.table = table

    async def on_submit(self, interaction: discord.Interaction):
        from cogs.match import process_result_modal

        await process_result_modal(
            interaction,
            self.table,
            self.p1_games.value,
            self.p2_games.value,
            self.winner.value
        )

        await send_ranking_summary(interaction)
        await auto_next_round(interaction)


# ==========================
# 結果入力ボタン
# ==========================
class ResultButtonView(discord.ui.View):
    def __init__(self, table: int):
        super().__init__(timeout=None)
        self.table = table

    @discord.ui.button(label="結果入力", style=discord.ButtonStyle.green)
    async def result_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ResultModal(self.table)
        await interaction.response.send_modal(modal)


# ==========================
# 大会終了ボタン
# ==========================
class EndTournamentView(discord.ui.View):
    def __init__(self, creator_id: int):
        super().__init__(timeout=None)
        self.creator_id = creator_id

    @discord.ui.button(label="大会終了", style=discord.ButtonStyle.red)
    async def end_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.creator_id:
            await interaction.response.send_message("❌ 大会作成者だけが終了できます。", ephemeral=True)
            return

        await end_tournament_internal(interaction)

        for item in self.children:
            item.disabled = True

        await interaction.message.edit(view=self)


# ==========================
# 参加 / 辞退 / 開始ボタン
# ==========================
class JoinLeaveStartView(discord.ui.View):
    def __init__(self, creator_id: int):
        super().__init__(timeout=None)
        self.creator_id = creator_id

    @discord.ui.button(label="参加する", style=discord.ButtonStyle.green)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        t = tournament_data.current_tournament
        if t is None:
            await interaction.response.send_message("❌ 大会がありません。", ephemeral=True)
            return

        if t["started"]:
            await interaction.response.send_message("❌ 大会開始後は参加できません。", ephemeral=True)
            return

        user = interaction.user
        if any(p["id"] == user.id for p in t["participants"]):
            await interaction.response.send_message("⚠️ すでに参加しています。", ephemeral=True)
            return

        player = tournament_data.create_player(user)
        t["participants"].append(player)

        embed = discord.Embed(
            title="🏆 大会を作成しました",
            description="下のボタンから参加できます！",
            color=discord.Color.gold()
        )
        embed.add_field(name="大会名", value=t["name"], inline=False)
        embed.add_field(name="参加人数", value=f"{len(t['participants'])}人", inline=True)
        embed.add_field(name="状態", value="募集中", inline=True)
        embed.add_field(name="形式", value=t["bo"], inline=True)

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="辞退する", style=discord.ButtonStyle.red)
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        t = tournament_data.current_tournament
        if t is None:
            await interaction.response.send_message("❌ 大会がありません。", ephemeral=True)
            return

        if t["started"]:
            await interaction.response.send_message("❌ 大会開始後は辞退できません。", ephemeral=True)
            return

        user = interaction.user
        participants = t["participants"]

        for p in participants:
            if p["id"] == user.id:
                participants.remove(p)

                embed = discord.Embed(
                    title="🏆 大会を作成しました",
                    description="下のボタンから参加できます！",
                    color=discord.Color.gold()
                )
                embed.add_field(name="大会名", value=t["name"], inline=False)
                embed.add_field(name="参加人数", value=f"{len(participants)}人", inline=True)
                embed.add_field(name="状態", value="募集中", inline=True)
                embed.add_field(name="形式", value=t["bo"], inline=True)

                await interaction.response.edit_message(embed=embed, view=self)
                return

        await interaction.response.send_message("❌ 参加していません。", ephemeral=True)

    @discord.ui.button(label="大会開始", style=discord.ButtonStyle.blurple)
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        t = tournament_data.current_tournament
        if t is None:
            await interaction.response.send_message("❌ 大会がありません。", ephemeral=True)
            return

        if interaction.user.id != self.creator_id:
            await interaction.response.send_message("❌ この大会の作成者だけが開始できます。", ephemeral=True)
            return

        if t["started"]:
            await interaction.response.send_message("⚠️ すでに開始されています。", ephemeral=True)
            return

        await interaction.response.defer()
        await start_tournament_internal(interaction)


# ==========================
# Tournament Cog
# ==========================
class Tournament(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="大会作成", description="新しい大会を作成します")
    @app_commands.describe(bo="BO1 または BO3 を選択")
    async def create_tournament(self, interaction: discord.Interaction, name: str, bo: str):

        if bo not in ["BO1", "BO3"]:
            await interaction.response.send_message("❌ BO は BO1 または BO3 を指定してください。", ephemeral=True)
            return

        tournament_data.current_tournament = {
            "name": name,
            "participants": [],
            "started": False,
            "round": 0,
            "matches": [],
            "creator_id": interaction.user.id,
            "bo": bo
        }

        embed = discord.Embed(
            title="🏆 大会を作成しました",
            description="下のボタンから参加できます！",
            color=discord.Color.gold()
        )
        embed.add_field(name="大会名", value=name, inline=False)
        embed.add_field(name="参加人数", value="0人", inline=True)
        embed.add_field(name="状態", value="募集中", inline=True)
        embed.add_field(name="形式", value=bo, inline=True)

        view = JoinLeaveStartView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tournament(bot))

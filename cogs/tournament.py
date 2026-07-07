import random

import discord
from discord.ext import commands
from discord import app_commands

import data.tournament_data as tournament_data
from cogs.match import send_round_notifications
from utils.swiss import swiss_pairing


GUILD_ID = 1238127187648057466


async def safe_interaction_send(interaction: discord.Interaction, *, content=None, embed=None, view=None, ephemeral=False):
    try:
        if not interaction.response.is_done():
            if view is None:
                await interaction.response.send_message(content=content, embed=embed, ephemeral=ephemeral)
            else:
                await interaction.response.send_message(content=content, embed=embed, view=view, ephemeral=ephemeral)
            return

        kwargs = {"content": content, "embed": embed, "ephemeral": ephemeral}
        if view is not None:
            kwargs["view"] = view
        await interaction.followup.send(**kwargs)
    except (discord.NotFound, discord.HTTPException):
        if interaction.channel is not None:
            try:
                if view is None:
                    await interaction.channel.send(content=content, embed=embed)
                else:
                    await interaction.channel.send(content=content, embed=embed, view=view)
            except Exception:
                pass


async def safe_defer_interaction(interaction: discord.Interaction, *, ephemeral=False):
    try:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=ephemeral)
            return True
    except (discord.NotFound, discord.HTTPException):
        return False
    return True


async def upsert_tournament_message(interaction: discord.Interaction, tournament: dict, embed: discord.Embed, view: discord.ui.View):
    message_id = tournament.get("message_id")
    channel = getattr(interaction, "channel", None)

    if channel is not None and message_id is not None:
        try:
            msg = await channel.fetch_message(message_id)
            await msg.edit(embed=embed, view=view)
            tournament["message_id"] = msg.id
            return msg
        except (discord.NotFound, discord.HTTPException):
            pass

    try:
        if interaction.response.is_done():
            msg = await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)
            msg = await interaction.original_response()
    except (discord.NotFound, discord.HTTPException):
        if channel is None:
            raise
        msg = await channel.send(embed=embed, view=view)

    tournament["message_id"] = msg.id
    tournament["channel_id"] = getattr(channel, "id", None)
    return msg


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
        await safe_interaction_send(interaction, content="❌ 大会がありません。")
        return

    embed = discord.Embed(
        title="🏁 大会終了",
        description=f"大会 **{t['name']}** を終了しました。",
        color=discord.Color.red()
    )

    await safe_interaction_send(interaction, embed=embed)
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
    print("[Tournament] auto_next_round called")
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

    await send_round_notifications(interaction, round_num, matches, bye_player)
    await send_ranking_summary(interaction)


# ==========================
# 大会開始処理
# ==========================
async def start_tournament_internal(interaction: discord.Interaction):
    print("[Tournament] start_tournament_internal called")
    t = tournament_data.current_tournament
    if t is None:
        print("[Tournament] no current tournament")
        await interaction.followup.send("❌ 大会がありません。")
        return

    participants = t.get("participants", [])
    if not isinstance(participants, list):
        participants = list(participants or [])

    print(f"[Tournament] starting tournament with {len(participants)} participants")
    print(f"[Tournament] participant data: {participants}")

    if len(participants) < 1:
        await interaction.followup.send("❌ 参加者がいません。")
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

    await send_round_notifications(interaction, 1, matches, bye_players[0] if bye_players else None)
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
        await interaction.response.defer()
        modal = ResultModal(self.table)
        await interaction.followup.send_modal(modal)


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

        await interaction.response.defer()
        await end_tournament_internal(interaction)

        for item in self.children:
            item.disabled = True

        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass


# ==========================
# 参加 / 辞退 / 開始ボタン
# ==========================
class JoinLeaveStartView(discord.ui.View):
    def __init__(self, creator_id: int):
        super().__init__(timeout=None)
        self.creator_id = creator_id

    @discord.ui.button(label="参加する", style=discord.ButtonStyle.green)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"[Button] join_button clicked by {interaction.user.id}")
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
        print(f"[Button] participant added: user_id={user.id} name={user.display_name}")

        try:
            print(f"[DM] sending join confirmation to user_id={user.id} name={user.display_name}")
            await user.send(f"【{t['name']}】に参加登録しました。大会開始後にラウンドごとの対戦相手をDMでお送りします。")
            print(f"[DM] join confirmation sent to user_id={user.id}")
        except discord.Forbidden as exc:
            print(f"[DM] join confirmation forbidden for user_id={user.id}: {exc}")
        except Exception as exc:
            print(f"[DM] join confirmation failed for user_id={user.id}: {exc}")

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
        print(f"[Button] start_button clicked by {interaction.user.id}")
        await interaction.response.defer()
        t = tournament_data.current_tournament
        if t is None:
            await safe_interaction_send(interaction, content="❌ 大会がありません。")
            return

        if interaction.user.id != self.creator_id:
            await safe_interaction_send(interaction, content="❌ この大会の作成者だけが開始できます。")
            return

        if t["started"]:
            await safe_interaction_send(interaction, content="⚠️ すでに開始されています。")
            return

        await start_tournament_internal(interaction)


# ==========================
# Tournament Cog
# ==========================
class Tournament(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="大会作成", description="新しい大会を作成します")
    @app_commands.describe(bo="BO1 または BO3 を選択")
    async def create_tournament(self, interaction: discord.Interaction, name: str, bo: str):
        if bo not in ["BO1", "BO3"]:
            await interaction.response.send_message("❌ BO は BO1 または BO3 を指定してください。", ephemeral=True)
            return

        await safe_defer_interaction(interaction)

        previous_tournament = tournament_data.current_tournament
        previous_message_id = None
        previous_channel_id = None
        if isinstance(previous_tournament, dict):
            previous_message_id = previous_tournament.get("message_id")
            previous_channel_id = previous_tournament.get("channel_id")

        tournament_data.current_tournament = {
            "name": name,
            "participants": [],
            "started": False,
            "round": 0,
            "matches": [],
            "creator_id": interaction.user.id,
            "bo": bo,
            "message_id": previous_message_id,
            "channel_id": previous_channel_id
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
        await upsert_tournament_message(interaction, tournament_data.current_tournament, embed, view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tournament(bot))

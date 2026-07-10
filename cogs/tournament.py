import random

import discord
from discord.ext import commands
from discord import app_commands

import data.tournament_data as tournament_data
from cogs.match import send_round_notifications
from utils.swiss import swiss_pairing


GUILD_ID = 1238127187648057466


# ==========================
# 安全送信
# ==========================
async def safe_interaction_send(
    interaction: discord.Interaction,
    *,
    content=None,
    embed=None,
    view=None,
    ephemeral=False
):
    try:
        # まだ response が未送信なら response.send_message を使う
        if not interaction.response.is_done():
            if view is None:
                await interaction.response.send_message(
                    content=content,
                    embed=embed,
                    ephemeral=ephemeral
                )
            else:
                await interaction.response.send_message(
                    content=content,
                    embed=embed,
                    view=view,
                    ephemeral=ephemeral
                )
            return

        # response が既に送信済みなら followup.send を使う
        if view is None:
            await interaction.followup.send(
                content=content,
                embed=embed,
                ephemeral=ephemeral
            )
        else:
            await interaction.followup.send(
                content=content,
                embed=embed,
                view=view,
                ephemeral=ephemeral
            )

    except Exception:
        # interaction が壊れている場合は channel に直接送信
        if interaction.channel:
            try:
                if view is None:
                    await interaction.channel.send(
                        content=content,
                        embed=embed
                    )
                else:
                    await interaction.channel.send(
                        content=content,
                        embed=embed,
                        view=view
                    )
            except:
                pass


async def safe_defer_interaction(
    interaction: discord.Interaction, *, ephemeral: bool = False
) -> bool:
    try:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=ephemeral)
            return True
    except (discord.NotFound, discord.HTTPException):
        return False
    return True


# ==========================
# 大会メッセージ更新
# ==========================
async def upsert_tournament_message(
    interaction: discord.Interaction,
    tournament: dict,
    embed: discord.Embed,
    view: discord.ui.View,
):
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
# ラウンドごとの順位表送信
# ==========================
async def send_ranking_summary(interaction):
    t = tournament_data.current_tournament
    if t is None:
        return

    ranking = tournament_data.sort_players()

    # ★ 勝敗のみ（wins-losses）を表示
    text = "\n".join([
        f"{i+1}. {p['name']} - {p['match_points']}点 ({p['wins']}-{p['losses']})"
        for i, p in enumerate(ranking)
    ])

    embed = discord.Embed(
        title=f"📊 ラウンド{t['round']} 結果まとめ",
        color=discord.Color.blue()
    )
    embed.add_field(name="順位表（勝ち点＋勝敗）", value=text, inline=False)

    view = EndTournamentView(t["creator_id"])

    # 固定メッセージ更新
    if t.get("ranking_message"):
        try:
            msg = await interaction.channel.fetch_message(t["ranking_message"])
            await msg.edit(embed=embed, view=view)
            return
        except:
            pass

    # 新規送信
    msg = await interaction.followup.send(embed=embed, view=view)
    t["ranking_message"] = msg.id


# ==========================
# ボタン無効化
# ==========================
async def disable_buttons(interaction: discord.Interaction):
    t = tournament_data.current_tournament
    if t is None:
        return

    bot = interaction.client

    view = JoinLeaveStartView(bot, t["creator_id"])
    view.join_button.disabled = True
    view.leave_button.disabled = True
    view.start_button.disabled = True

    channel = bot.get_channel(t["channel_id"])
    if channel and t["message_id"]:
        try:
            msg = await channel.fetch_message(t["message_id"])
            await msg.edit(view=view)
        except Exception:
            pass


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
        color=discord.Color.red(),
    )

    await safe_interaction_send(interaction, embed=embed)
    tournament_data.reset()


# ==========================
# 総当たり終了判定
# ==========================
def is_round_robin_finished(t: dict) -> bool:
    participants = t["participants"]
    N = len(participants)
    return all(len(p["opponents"]) >= N - 1 for p in participants)


# ==========================
# 自動ラウンド移行（BYE opponents 更新＋DM通知追加）
# ==========================
async def auto_next_round(interaction):
    print("[Tournament] auto_next_round called")

    t = tournament_data.current_tournament
    if t is None:
        return

    # 全試合終了していなければ次ラウンドに進まない
    if not tournament_data.all_matches_finished():
        return

    # ==========================
    # 総当たり終了判定
    # ==========================
    if is_round_robin_finished(t):
        ranking = tournament_data.sort_players()
        winner_final = ranking[0]

        names = "\n".join([p["name"] for p in ranking])

        await interaction.followup.send(
            f"🏁 総当たりが終了しました！\n"
            f"🎉 優勝者は **{winner_final['name']}** さんです！おめでとうございます！\n\n"
            f"👥 参加者一覧：\n{names}"
        )

        await end_tournament_internal(interaction)
        return

    # ==========================
    # ラウンド番号更新
    # ==========================
    t["round"] += 1

    # BYE 初期化
    for p in t["participants"]:
        p["bye"] = False

    # ==========================
    # スイスドローペアリング
    # ==========================
    matches_raw, bye_player = swiss_pairing(t)

    # BYE の opponents を更新
    if bye_player:
        for p in t["participants"]:
            if p["id"] != bye_player["id"]:
                bye_player["opponents"].append(p["id"])

    # ==========================
    # 新しいラウンドの試合を生成
    # ==========================
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

    # ==========================
    # BYE通知（加点なし）
    # ==========================
    if bye_player:
        await interaction.followup.send(
            f"BYE: {bye_player['name']}（加点なし）"
        )

    # ==========================
    # ランキング送信
    # ==========================
    await send_ranking_summary(interaction)

    # ==========================
    # 次ラウンドの対戦表を DM 送信
    # ==========================
    await send_round_notifications(
        interaction,
        t["round"],
        matches,
        bye_player if bye_player else None
    )


# ==========================
# 大会開始処理（完全版・selfなし）
# ==========================
async def start_tournament_internal(interaction: discord.Interaction):
    print("[Tournament] start_tournament_internal called")

    t = tournament_data.current_tournament
    if t is None:
        await interaction.followup.send("❌ 大会データがありません。")
        return

    participants = t["participants"]

    if len(participants) < 2:
        await interaction.followup.send("❌ 参加者が2人以上必要です。")
        return

    # 大会開始フラグ
    t["started"] = True
    t["round"] = 1

    # 参加者初期化
    for p in participants:
        p["wins"] = 0
        p["losses"] = 0
        p["draws"] = 0
        p["match_points"] = 0
        p["opponents"] = []
        p["dm_score"] = None
        p["bye"] = False

    # ==========================
    # ペアリング生成
    # ==========================
    matches = []
    table = 1
    i = 0

    while i < len(participants):
        # ★ 最後の1人 → BYE
        if i == len(participants) - 1:
            bye_player = participants[i]
            bye_player["bye"] = True

            # ★ BYE は加点なし
            bye_player["match_points"] += 0

            # ★ 総当たり終了判定のため opponents を全員追加
            for p in participants:
                if p["id"] != bye_player["id"]:
                    bye_player["opponents"].append(p["id"])

            break

        # 通常の試合
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

    # ==========================
    # ラウンド開始通知（DM送信）
    # ==========================
    await interaction.followup.send("🏁 大会を開始しました！ラウンド1をDMで送信します。")

    await send_round_notifications(
        interaction,
        t["round"],
        matches,
        bye_player if "bye_player" in locals() else None
    )

    # ランキング初期表示
    await send_ranking_summary(interaction)



# ==========================
# 参加登録モーダル
# ==========================
class JoinModal(discord.ui.Modal, title="参加登録"):
    player_name = discord.ui.TextInput(
        label="プレイヤー名 / チーム名",
        placeholder="例：しだっくす、Team A など",
        max_length=50,
    )

    def __init__(self, interaction: discord.Interaction):
        super().__init__()
        self.client = interaction.client

    async def on_submit(self, interaction: discord.Interaction):
        t = tournament_data.current_tournament
        user = interaction.user

        player = tournament_data.create_player(user)
        player["name"] = self.player_name.value
        t["participants"].append(player)

        try:
            await user.send(
                f"【{t['name']}】に参加登録しました。\n"
                f"登録名：{player['name']}"
            )
        except Exception:
            pass

        embed = discord.Embed(
            title="🏆 大会を作成しました",
            description="下のボタンから参加できます！",
            color=discord.Color.gold(),
        )
        embed.add_field(name="大会名", value=t["name"], inline=False)
        embed.add_field(
            name="参加人数", value=f"{len(t['participants'])}人", inline=True
        )
        embed.add_field(name="状態", value="募集中", inline=True)
        embed.add_field(name="形式", value=t["bo"], inline=True)

        view = JoinLeaveStartView(self.client, t["creator_id"])

        await interaction.response.edit_message(embed=embed, view=view)


# ==========================
# 大会終了ボタン
# ==========================
class EndTournamentView(discord.ui.View):
    def __init__(self, creator_id: int):
        super().__init__(timeout=None)
        self.creator_id = creator_id

    @discord.ui.button(label="大会終了", style=discord.ButtonStyle.red)
    async def end_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.creator_id:
            await interaction.response.send_message(
                "❌ 大会作成者だけが終了できます。", ephemeral=True
            )
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
    def __init__(self, bot: commands.Bot, creator_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.creator_id = creator_id

    @discord.ui.button(label="参加する", style=discord.ButtonStyle.green)
    async def join_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        print(f"[Button] join_button clicked by {interaction.user.id}")
        t = tournament_data.current_tournament
        if t is None:
            await interaction.response.send_message(
                "❌ 大会がありません。", ephemeral=True
            )
            return

        if t["started"]:
            await interaction.response.send_message(
                "❌ 大会開始後は参加できません。", ephemeral=True
            )
            return

        user = interaction.user
        if any(p["id"] == user.id for p in t["participants"]):
            await interaction.response.send_message(
                "⚠️ すでに参加しています。", ephemeral=True
            )
            return

        modal = JoinModal(interaction)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="辞退する", style=discord.ButtonStyle.red)
    async def leave_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        t = tournament_data.current_tournament
        if t is None:
            await interaction.response.send_message(
                "❌ 大会がありません。", ephemeral=True
            )
            return

        if t["started"]:
            await interaction.response.send_message(
                "❌ 大会開始後は辞退できません。", ephemeral=True
            )
            return

        user = interaction.user
        participants = t["participants"]

        for p in participants:
            if p["id"] == user.id:
                participants.remove(p)

                embed = discord.Embed(
                    title="🏆 大会を作成しました",
                    description="下のボタンから参加できます！",
                    color=discord.Color.gold(),
                )
                embed.add_field(name="大会名", value=t["name"], inline=False)
                embed.add_field(
                    name="参加人数", value=f"{len(participants)}人", inline=True
                )
                embed.add_field(name="状態", value="募集中", inline=True)
                embed.add_field(name="形式", value=t["bo"], inline=True)

                await interaction.response.edit_message(embed=embed, view=self)
                return

        await interaction.response.send_message(
            "❌ 参加していません。", ephemeral=True
        )

    @discord.ui.button(label="大会開始", style=discord.ButtonStyle.blurple)
    async def start_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        print(f"[Button] start_button clicked by {interaction.user.id}")
        await interaction.response.defer()

        t = tournament_data.current_tournament
        if t is None:
            await safe_interaction_send(interaction, content="❌ 大会がありません。")
            return

        if interaction.user.id != self.creator_id:
            await safe_interaction_send(
                interaction, content="❌ この大会の作成者だけが開始できます。"
            )
            return

        if t["started"]:
            await safe_interaction_send(
                interaction, content="⚠️ すでに開始されています。"
            )
            return

        await start_tournament_internal(interaction)

        self.join_button.disabled = True
        self.leave_button.disabled = True
        self.start_button.disabled = True

        channel = self.bot.get_channel(t["channel_id"])
        if channel and t["message_id"]:
            try:
                msg = await channel.fetch_message(t["message_id"])
                await msg.edit(view=self)
            except Exception:
                pass


# ==========================
# Tournament Cog
# ==========================
class Tournament(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ==========================
    # /大会作成 コマンド
    # ==========================
    @app_commands.guilds(GUILD_ID)
    @app_commands.command(name="大会作成", description="新しい大会を作成します")
    @app_commands.describe(bo="BO1 または BO3 を選択")
    async def create_tournament(
        self, interaction: discord.Interaction, name: str, bo: str
    ):
        if bo not in ["BO1", "BO3"]:
            await interaction.response.send_message(
                "❌ BO は BO1 または BO3 を指定してください。", ephemeral=True
            )
            return

        await safe_defer_interaction(interaction)

        tournament_data.current_tournament = {
            "name": name,
            "participants": [],
            "started": False,
            "round": 0,
            "matches": [],
            "creator_id": interaction.user.id,
            "bo": bo,
            "message_id": None,
            "channel_id": interaction.channel.id,
        }

        embed = discord.Embed(
            title="🏆 大会を作成しました",
            description="下のボタンから参加できます！",
            color=discord.Color.gold(),
        )
        embed.add_field(name="大会名", value=name, inline=False)
        embed.add_field(name="参加人数", value="0人", inline=True)
        embed.add_field(name="状態", value="募集中", inline=True)
        embed.add_field(name="形式", value=bo, inline=True)

        view = JoinLeaveStartView(self.bot, interaction.user.id)

        await upsert_tournament_message(
            interaction, tournament_data.current_tournament, embed, view
        )

    # ==========================
    # DM結果入力（BO1/BO3 共通・数字だけ）
    # ==========================
    async def handle_dm_score(self, message: discord.Message):
            t = tournament_data.current_tournament
            if t is None or not t["started"]:
                return

            print(f"[DM-RECEIVE] from {message.author.id}: {message.content}")

            content = message.content.strip()
            user_id = message.author.id

            # ==========================
            # 数字チェック
            # ==========================
            if not content.isdigit():
                await message.channel.send("❌ セット数は数字だけで送ってください。例：2")
                return

            score = int(content)

            # ==========================
            # 試合取得
            # ==========================
            match = None
            for m in t["matches"]:
                if m["player1"]["id"] == user_id or m["player2"]["id"] == user_id:
                    match = m
                    break

            if match is None:
                await message.channel.send("❌ あなたの試合が見つかりません。")
                return

            p1 = match["player1"]
            p2 = match["player2"]

            # DMスコア記録
            if p1["id"] == user_id:
                p1["dm_score"] = score
            else:
                p2["dm_score"] = score

            await message.channel.send("✅ セット数を受け取りました。")

            # 片方だけなら待機
            if p1.get("dm_score") is None or p2.get("dm_score") is None:
                print("[DM-RECEIVE] waiting for opponent score...")
                return

            print("[DM-RECEIVE] both scores received, processing result...")

            s1 = p1["dm_score"]
            s2 = p2["dm_score"]

            # ==========================
            # 勝敗判定（引き分けなし）
            # ==========================
            if s1 > s2:
                winner = p1
                loser = p2
            elif s2 > s1:
                winner = p2
                loser = p1
            else:
                # ★ 引き分けは存在しない → 同点なら player1 を勝者扱い
                winner = p1
                loser = p2

            match["finished"] = True
            match["winner"] = winner["id"]

            # ==========================
            # 対戦履歴
            # ==========================
            p1["opponents"].append(p2["id"])
            p2["opponents"].append(p1["id"])

            # ==========================
            # 勝敗カウント
            # ==========================
            winner["wins"] += 1
            loser["losses"] += 1

            # ==========================
            # ★ 勝点は「セット数×2」で両者に付与
            # ==========================
            p1["match_points"] += s1 * 2
            p2["match_points"] += s2 * 2

            # ==========================
            # OMW / OGW 更新
            # ==========================
            tournament_data.update_omw(t)
            tournament_data.update_ogw(t)

            # ==========================
            # DM通知
            # ==========================
            try:
                u1 = await self.bot.fetch_user(p1["id"])
                u2 = await self.bot.fetch_user(p2["id"])

                msg = (
                    f"🏆 勝者：{winner['name']}（{s1}-{s2}）\n"
                    f"📊 勝点：{p1['name']} {s1*2}点 / {p2['name']} {s2*2}点"
                )

                await u1.send(msg)
                await u2.send(msg)
            except:
                pass

            # スコアリセット
            p1["dm_score"] = None
            p2["dm_score"] = None

            # ==========================
            # DummyInteraction（response付き）
            # ==========================
            channel = self.bot.get_channel(t["channel_id"])

            class DummyInteraction:
                def __init__(self, bot, channel):
                    self.client = bot
                    self.channel = channel

                    class DummyResponse:
                        def is_done(self):
                            return True

                        async def send_message(self, *args, **kwargs):
                            await channel.send(*args, **kwargs)

                    self.response = DummyResponse()

                    class DummyFollowup:
                        async def send(self, *args, **kwargs):
                            await channel.send(*args, **kwargs)

                    self.followup = DummyFollowup()

            dummy = DummyInteraction(self.bot, channel)

            # ランキング更新
            await send_ranking_summary(dummy)

            # 総当たり終了判定
            if is_round_robin_finished(t):
                ranking = tournament_data.sort_players()
                winner_final = ranking[0]

                names = "\n".join([p["name"] for p in ranking])

                await channel.send(
                    f"🏁 総当たりが終了しました！\n"
                    f"🎉 優勝者は **{winner_final['name']}** さんです！おめでとうございます！\n\n"
                    f"👥 参加者一覧：\n{names}"
                )

                await end_tournament_internal(dummy)
                return

            # 次ラウンドへ
            await auto_next_round(dummy)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tournament(bot))

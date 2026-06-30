import discord
from discord.ext import commands
from discord import app_commands

import data.tournament_data as tournament_data


GUILD_ID = 1238127187648057466


class Player(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==========================
    # /参加（スラッシュコマンド）
    # ==========================
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="参加", description="大会に参加します")
    async def join(self, interaction: discord.Interaction):

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

        embed = discord.Embed(title="✅ 参加受付", color=discord.Color.green())
        embed.add_field(name="参加者", value=user.mention, inline=False)
        embed.add_field(
            name="現在の参加人数",
            value=f"{len(t['participants'])}人",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    # ==========================
    # /辞退（スラッシュコマンド）
    # ==========================
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="辞退", description="大会への参加を辞退します")
    async def leave(self, interaction: discord.Interaction):

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

                embed = discord.Embed(title="📤 辞退しました", color=discord.Color.orange())
                embed.add_field(name="プレイヤー", value=user.mention, inline=False)
                embed.add_field(name="現在の参加人数", value=f"{len(participants)}人", inline=False)

                await interaction.response.send_message(embed=embed)
                return

        await interaction.response.send_message("❌ 参加していません。", ephemeral=True)


# ==========================
# ボタン用：参加処理（大会作成Embedを更新するためにメッセージを送らない）
# ==========================
async def join_user(interaction: discord.Interaction, user: discord.User):
    t = tournament_data.current_tournament
    if t is None:
        return False  # tournament.py 側でエラー表示

    if any(p["id"] == user.id for p in t["participants"]):
        return False

    player = tournament_data.create_player(user)
    t["participants"].append(player)

    return True  # 成功したことだけ返す


# ==========================
# ボタン用：辞退処理
# ==========================
async def leave_user(interaction: discord.Interaction, user: discord.User):
    t = tournament_data.current_tournament
    if t is None:
        return False

    for p in t["participants"]:
        if p["id"] == user.id:
            t["participants"].remove(p)
            return True

    return False


async def setup(bot):
    await bot.add_cog(Player(bot))

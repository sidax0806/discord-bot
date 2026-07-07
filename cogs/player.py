import discord
from discord.ext import commands
from discord import app_commands

import data.tournament_data as tournament_data


GUILD_ID = 1238127187648057466


class Player(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

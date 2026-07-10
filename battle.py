import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))

# ==========================
# Intents 設定
# ==========================
intents = discord.Intents.default()
intents.dm_messages = True
intents.guild_messages = True
intents.message_content = True  # ★ DMレシーブに必須


# ==========================
# Bot クラス
# ==========================
class BattleBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        # Cog読み込み
        extensions = [
            "cogs.tournament_admin",
            "cogs.tournament",
            "cogs.player",
            "cogs.match",
            "cogs.ranking",
            "cogs.utility",
        ]

        for extension in extensions:
            await self.load_extension(extension)
            print(f"{extension} を読み込みました")

        # スラッシュコマンド同期（ギルド限定）
        guild = discord.Object(id=GUILD_ID)
        synced = await self.tree.sync(guild=guild)
        print(f"{len(synced)}個のコマンドを同期しました（ギルドID: {GUILD_ID}）")


bot = BattleBot()


# ==========================
# Bot 起動ログ
# ==========================
@bot.event
async def on_ready():
    print(f"{bot.user} がオンラインになりました！")


# ==========================
# Interaction ログ
# ==========================
@bot.event
async def on_interaction(interaction):
    if interaction.type.name != "application_command":
        return
    print(f"[Interaction] type={interaction.type} user={interaction.user} channel={getattr(interaction, 'channel', None)}")


# ==========================
# DM レシーブ（Tournament Cog のメソッドを呼び出す）
# ==========================
@bot.event
async def on_message(message):
    await bot.process_commands(message)

    # DM以外は無視
    if message.guild is not None:
        return

    # BOTは無視
    if message.author.bot:
        return

    # Tournament Cog のメソッドを呼び出す（★ここが重要）
    tournament_cog = bot.get_cog("Tournament")
    if tournament_cog:
        try:
            await tournament_cog.handle_dm_score(message)
        except Exception as e:
            print(f"[DM-ERROR] {e}")


# ==========================
# Bot 起動
# ==========================
bot.run(TOKEN)

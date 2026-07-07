import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))

intents = discord.Intents.default()
intents.dm_messages = True
intents.guild_messages = True


class BattleBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        # Cog読み込み（完成版）
        extensions = [
            "cogs.tournament",
            "cogs.player",
            "cogs.match",
            "cogs.ranking",
            "cogs.tournament_admin",   # ★追加
            "cogs.utility",            # ★追加
        ]

        for extension in extensions:
            await self.load_extension(extension)
            print(f"{extension} を読み込みました")

        # スラッシュコマンド同期
        synced = await self.tree.sync()
        print(f"{len(synced)}個のコマンドを同期しました")


bot = BattleBot()


@bot.event
async def on_ready():
    print(f"{bot.user} がオンラインになりました！")


@bot.event
async def on_interaction(interaction):
    if interaction.type.name != "application_command":
        return
    print(f"[Interaction] type={interaction.type} user={interaction.user} channel={getattr(interaction, 'channel', None)}")



bot.run(TOKEN)

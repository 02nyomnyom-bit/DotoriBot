# main.py
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from discord import Intents

load_dotenv()

# 외부 명령어
import help_command
import point_manager
import rock_paper_scissors
import dice_game

intents = discord.Intents.default()
intents.messages = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print("Online")
    
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="/", intents=intents)

    #명령어
    async def setup_hook(self):

        #포인트
        self.tree.add_command(point_manager.list_registered_users)
        self.tree.add_command(point_manager.unregister_user)

        #가위바위보
        self.tree.add_command(rock_paper_scissors.rps_command)

        #주사위 게임
        self.tree.add_command(dice_game.dice_command)


        #도움말
        slash_commands = [
        help_command.help_command,
        point_manager.register_command,
        point_manager.point_command,
        point_manager.point_check,
        point_manager.my_point_and_rank,
        point_manager.add_point_admin,
        point_manager.subtract_point_admin,
        point_manager.gift_point,
        point_manager.point_leaderboard
        ]


        for cmd in slash_commands:
            try:
                self.tree.add_command(cmd)
                print(f"✅ 등록됨: /{cmd.name}")
            except Exception as e:
                print(f"❌ 등록 실패: /{getattr(cmd, 'name', '알 수 없음')} - {e}")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"✅ 봇 로그인됨: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)}개의 슬래시 명령어가 디스코드에 동기화되었습니다.")
    except Exception as e:
        print(f"⚠️ 동기화 실패: {e}")

bot.run(TOKEN)
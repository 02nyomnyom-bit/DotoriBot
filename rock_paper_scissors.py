import random
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View
from typing import Literal, Optional

import point_manager

CHOICES = ["가위", "바위", "보"]
EMOJIS = {"가위": "✌", "바위": "✊", "보": "✋"}

def with_emoji(choice):
    return f"{EMOJIS.get(choice, '')} {choice}"

def determine_winner(p1, p2):
    if p1 == p2:
        return "무승부"
    wins = {"가위": "보", "바위": "가위", "보": "바위"}
    return "플레이어 1 승" if wins[p1] == p2 else "플레이어 2 승"

active_games_by_user = set()

class SinglePlayView(View):
    def __init__(self, user, channel_id, betting_point=5):
        super().__init__(timeout=60)
        self.user = user
        self.channel_id = channel_id
        self.betting_point = betting_point

    async def on_timeout(self):
        await self._expire_game("⏰ 시간 초과로 싱글 게임이 종료되었습니다.")

    async def _expire_game(self, msg):
        try: await self.user.send(msg)
        except: pass
        active_games_by_user.discard(self.user.id)
        self.stop()

    @discord.ui.button(label="✌", style=discord.ButtonStyle.primary)
    async def scissors(self, interaction, button): await self.handle_choice(interaction, "가위")

    @discord.ui.button(label="✊", style=discord.ButtonStyle.success)
    async def rock(self, interaction, button): await self.handle_choice(interaction, "바위")

    @discord.ui.button(label="✋", style=discord.ButtonStyle.danger)
    async def paper(self, interaction, button): await self.handle_choice(interaction, "보")

    async def handle_choice(self, interaction, choice):
        if interaction.user != self.user:
            return await interaction.response.send_message("❗ 본인의 게임만 진행할 수 있어요.", ephemeral=True)

        user_id = str(self.user.id)
        if not point_manager.is_registered(user_id):
            point_manager.register_user(user_id)

        if point_manager.get_point(user_id) < self.betting_point:
            return await interaction.response.send_message(f"❌ 잔액 부족! 현재: {point_manager.get_point(user_id)}원", ephemeral=True)

        bot_choice = random.choice(CHOICES)
        result = determine_winner(choice, bot_choice)

        if result == "플레이어 1 승":
            reward = self.betting_point * 2
            point_manager.add_point(user_id, reward)
            result_msg = f"🎉 승리! +{reward}점 (2배 보상)"
        elif result == "플레이어 2 승":
            point_manager.add_point(user_id, -self.betting_point)
            result_msg = f"😢 패배! -{self.betting_point}점"
        else:
            result_msg = "🤝 무승부! 현금 변동 없음."

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content=(
                f"🎯 플레이어: {with_emoji(choice)}\n"
                f"🤖 딜러: {with_emoji(bot_choice)}\n"
                f"🏆 결과: {result_msg}\n"
                f"✅ 게임이 종료되었습니다."
            ),
            view=self
        )

        active_games_by_user.discard(self.user.id)
        self.stop()

class MultiPlayP1View(View):
    def __init__(self, user, channel_id, bet, opponent=None):
        super().__init__(timeout=60)
        self.user = user
        self.channel_id = channel_id
        self.bet = bet
        self.opponent = opponent
        self.choice = None

    async def on_timeout(self):
        try: await self.user.send("⏹️ 시간 초과로 게임이 종료되었습니다.")
        except: pass
        active_games_by_user.discard(self.user.id)
        if self.opponent:
            active_games_by_user.discard(self.opponent.id)
        self.stop()

    @discord.ui.button(label="✌", style=discord.ButtonStyle.primary)
    async def scissors(self, interaction, button): await self.set_choice(interaction, "가위")

    @discord.ui.button(label="✊", style=discord.ButtonStyle.success)
    async def rock(self, interaction, button): await self.set_choice(interaction, "바위")

    @discord.ui.button(label="✋", style=discord.ButtonStyle.danger)
    async def paper(self, interaction, button): await self.set_choice(interaction, "보")

    async def set_choice(self, interaction, choice):
        if interaction.user != self.user:
            return await interaction.response.send_message("❗ 본인만 선택할 수 있어요.", ephemeral=True)

        self.choice = choice
        await interaction.response.send_message("✅ 선택 완료! 상대방을 기다립니다.", ephemeral=True)
        self.stop()

class MultiPlayP2View(View):
    def __init__(self, p1_user, p1_choice, bet, opponent=None):
        super().__init__(timeout=60)
        self.p1_user = p1_user
        self.p1_choice = p1_choice
        self.bet = bet
        self.opponent = opponent
        self.p2_user = None

    async def on_timeout(self):
        for uid in [self.p1_user.id, getattr(self.p2_user, 'id', None)]:
            active_games_by_user.discard(uid)
        self.stop()

    @discord.ui.button(label="✌", style=discord.ButtonStyle.primary)
    async def scissors(self, interaction, button): await self.handle_choice(interaction, "가위")

    @discord.ui.button(label="✊", style=discord.ButtonStyle.success)
    async def rock(self, interaction, button): await self.handle_choice(interaction, "바위")

    @discord.ui.button(label="✋", style=discord.ButtonStyle.danger)
    async def paper(self, interaction, button): await self.handle_choice(interaction, "보")

    async def handle_choice(self, interaction, choice):
        if self.p1_choice is None:
            return await interaction.response.send_message("❗ 상대방이 아직 선택을 완료하지 않았습니다.", ephemeral=True)

        if interaction.user == self.p1_user:
            return await interaction.response.send_message("❗ 본인과는 게임할 수 없습니다.", ephemeral=True)

        if self.opponent and interaction.user != self.opponent:
            return await interaction.response.send_message("❗ 이 게임에 참여할 수 없습니다.", ephemeral=True)

        if self.p2_user:
            return await interaction.response.send_message("❗ 이미 참여한 플레이어가 있습니다.", ephemeral=True)

        p2_id = str(interaction.user.id)
        if not point_manager.is_registered(p2_id):
            point_manager.register_user(p2_id)

        if point_manager.get_point(p2_id) < self.bet:
            return await interaction.response.send_message(
                f"❌ {interaction.user.mention}님의 잔액이 부족하여 게임에 참여할 수 없습니다.",
                ephemeral=True
            )

        self.p2_user = interaction.user

        p1_id = str(self.p1_user.id)
        if point_manager.get_point(p1_id) < self.bet:
            return await interaction.response.send_message("❌ 상대방의 잔액이 부족하여 게임을 시작할 수 없습니다.", ephemeral=True)

        result = determine_winner(self.p1_choice, choice)

        if result == "플레이어 1 승":
            point_manager.add_point(p1_id, self.bet)
            point_manager.add_point(p2_id, -self.bet)
            result_msg = f"🏅 {self.p1_user.mention} 승! +{self.bet}원"
        elif result == "플레이어 2 승":
            point_manager.add_point(p2_id, self.bet)
            point_manager.add_point(p1_id, -self.bet)
            result_msg = f"🏅 {self.p2_user.mention} 승! +{self.bet}원"
        else:
            result_msg = "🤝 무승부! 포인트 변동 없음."

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content=(
                f"{self.p1_user.mention}: {with_emoji(self.p1_choice)}\n"
                f"{self.p2_user.mention}: {with_emoji(choice)}\n"
                f"🏆 결과: {result_msg}\n"
                f"✅ 게임이 종료되었습니다."
            ),
            view=self
        )

        active_games_by_user.discard(self.p1_user.id)
        active_games_by_user.discard(self.p2_user.id)
        self.stop()

@app_commands.command(name="가위바위보", description="가위바위보 게임 시작")
@app_commands.describe(
    모드="싱글 또는 멀티 선택",
    배팅="배팅 안할시 기본 10원만 배팅됨. 배팅할 현금 (1~1000원)",
    상대방="(선택 사항) 상대 유저를 지정하세요 (멀티 전용)"
)
async def rps_command(interaction: discord.Interaction, 모드: Literal["싱글", "멀티"], 배팅: int = 10, 상대방: Optional[discord.User] = None):
    uid = interaction.user.id

    if 모드 == "싱글":
        if 배팅 < 1 or 배팅 > 1000:
            return await interaction.response.send_message("❗ 싱글 모드는 1~1000원 사이여야 합니다.", ephemeral=True)

    user_id = str(interaction.user.id)
    if not point_manager.is_registered(user_id):
        point_manager.register_user(user_id)

    if point_manager.get_point(user_id) < 배팅:
        return await interaction.response.send_message(
            f"❌ 현재 잔액이 부족하여 게임을 시작할 수 없습니다.\n💰 현재 잔액: {point_manager.get_point(user_id)}원",
            ephemeral=True
        )

    elif 모드 == "멀티":
        if 배팅 < 1:
            return await interaction.response.send_message("❗ 멀티 모드는 1원 이상만 허용됩니다.", ephemeral=True)

    if uid in active_games_by_user:
        return await interaction.response.send_message("❗ 이미 진행 중인 게임이 있습니다.", ephemeral=True)

    active_games_by_user.add(uid)

    if 모드 == "싱글":
        await interaction.response.send_message(
            f"🎮 싱글 가위바위보 시작! 배팅: {배팅}원\n선택해주세요!",
            view=SinglePlayView(interaction.user, interaction.channel.id, 배팅)
        )
        return

    if 상대방:
        if 상대방.id == uid:
            active_games_by_user.discard(uid)
            return await interaction.response.send_message("❗ 자신과는 게임할 수 없습니다.", ephemeral=True)
        if 상대방.id in active_games_by_user:
            active_games_by_user.discard(uid)
            return await interaction.response.send_message("❗ 상대방이 이미 게임 중입니다.", ephemeral=True)

        active_games_by_user.add(상대방.id)
        p1_view = MultiPlayP1View(interaction.user, interaction.channel.id, 배팅, 상대방)

        await interaction.response.send_message(
            f"🎮 멀티 가위바위보 (지정) 시작! 배팅: {배팅}원\n{interaction.user.mention}님, 선택해주세요.",
            view=p1_view
        )
    else:
        p1_view = MultiPlayP1View(interaction.user, interaction.channel.id, 배팅)
        await interaction.response.send_message(
            f"🎮 멀티 가위바위보 (공개) 시작! 배팅: {배팅}원\n{interaction.user.mention}님, 선택해주세요.",
            view=p1_view
        )

    await p1_view.wait()

    if not p1_view.choice:
        active_games_by_user.discard(uid)
        if 상대방:
            active_games_by_user.discard(상대방.id)
        return

    await interaction.followup.send(
        f"{interaction.user.mention}님이 선택을 완료했습니다!\n"
        f"{상대방.mention if 상대방 else '도전할 플레이어'}님, 아래 버튼을 눌러 주세요!",
        view=MultiPlayP2View(interaction.user, p1_view.choice, 배팅, 상대방)
    )

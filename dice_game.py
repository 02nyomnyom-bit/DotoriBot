import random
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
from typing import Literal, Optional
import point_manager

# 🎲 주사위 이모지 매핑
DICE_EMOJIS = {
    1: "⚀",
    2: "⚁",
    3: "⚂",
    4: "⚃",
    5: "⚄",
    6: "⚅"
}


# ✅ 싱글 주사위 게임
class SingleDiceView(View):
    def __init__(self, user: discord.User, bet: int):
        super().__init__(timeout=60)
        self.user = user
        self.bet = bet

    @discord.ui.button(label="🎲 주사위 굴리기", style=discord.ButtonStyle.primary)
    async def roll_dice(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("❗ 본인만 주사위를 굴릴 수 있어요.", ephemeral=True)

        uid = str(self.user.id)
        if not point_manager.is_registered(uid):
            return await interaction.response.send_message("❗ 먼저 `/등록`을 해주세요.", ephemeral=True)

        if point_manager.get_point(uid) < self.bet:
            return await interaction.response.send_message("❌ 잔액이 부족합니다.", ephemeral=True)

        # 초기 메시지
        await interaction.response.send_message(f"{self.user.mention} 주사위를 굴리는 중... 🎲", view=self)
        msg = await interaction.original_response()

        # 애니메이션
        for _ in range(5):
            temp_roll = random.randint(1, 6)
            await msg.edit(content=f"{self.user.mention} 주사위를 굴리는 중... {DICE_EMOJIS[temp_roll]}")
            await asyncio.sleep(0.3)

        user_roll = random.randint(1, 6)
        bot_roll = random.randint(1, 6)

        if user_roll > bot_roll:
            reward = self.bet * 2
            point_manager.add_point(uid, reward)
            result = f"🎉 승리! +{reward}점"
        elif user_roll < bot_roll:
            point_manager.add_point(uid, -self.bet)
            result = f"😢 패배! -{self.bet}점"
        else:
            result = "🤝 무승부! 포인트 변동 없음."

        button.disabled = True
        await msg.edit(
            content=(
                f"🎯 {self.user.mention}의 주사위: {DICE_EMOJIS[user_roll]}\n"
                f"🤖 딜러의 주사위: {DICE_EMOJIS[bot_roll]}\n"
                f"🏆 결과: {result}"
            ),
            view=self
        )
        self.stop()


# ✅ 멀티 주사위 게임
class MultiDiceView(View):
    def __init__(self, player1: discord.User, bet: int, opponent: Optional[discord.User] = None):
        super().__init__(timeout=60)
        self.player1 = player1
        self.opponent = opponent
        self.bet = bet
        self.player1_roll = None
        self.player2_roll = None
        self.player2_user = None
        self.rolled_users = set()

    @discord.ui.button(label="🎲 주사위 굴리기", style=discord.ButtonStyle.success)
    async def roll(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = str(interaction.user.id)

        # 등록 검사
        if not point_manager.is_registered(uid):
            return await interaction.response.send_message("❗ 먼저 `/등록`을 해주세요.", ephemeral=True)

        # 참가 제한 검사
        if self.opponent:
            if interaction.user not in [self.player1, self.opponent]:
                return await interaction.response.send_message("❌ 이 게임에 참여할 수 없습니다.", ephemeral=True)
        else:
            if self.player2_user and interaction.user != self.player2_user:
                return await interaction.response.send_message("❌ 이미 두 명이 참여 중입니다.", ephemeral=True)

        if interaction.user.id in self.rolled_users:
            return await interaction.response.send_message("⚠ 이미 주사위를 굴렸습니다.", ephemeral=True)

        if point_manager.get_point(uid) < self.bet:
            return await interaction.response.send_message("❌ 포인트가 부족합니다.", ephemeral=True)

        # 주사위 굴리기
        roll = random.randint(1, 6)
        self.rolled_users.add(interaction.user.id)

        if interaction.user == self.player1:
            self.player1_roll = roll
        else:
            self.player2_user = interaction.user
            self.player2_roll = roll

        await interaction.response.send_message(
            f"{interaction.user.mention}의 주사위: {DICE_EMOJIS[roll]}", ephemeral=True
        )

        # 결과 계산
        if self.player1_roll and self.player2_roll:
            p1_id = str(self.player1.id)
            p2_user = self.player2_user
            p2_id = str(p2_user.id)

            msg = await interaction.original_response()

            # 애니메이션
            for _ in range(5):
                temp_roll1 = random.randint(1, 6)
                temp_roll2 = random.randint(1, 6)
                await msg.edit(content=(
                    f"{self.player1.mention} 주사위를 굴리는 중... {DICE_EMOJIS[temp_roll1]}\n"
                    f"{p2_user.mention} 주사위를 굴리는 중... {DICE_EMOJIS[temp_roll2]}"
                ))
                await asyncio.sleep(0.3)

            # 실제 결과
            if self.player1_roll > self.player2_roll:
                point_manager.add_point(p1_id, self.bet)
                point_manager.add_point(p2_id, -self.bet)
                result = f"🏆 {self.player1.mention} 승리! +{self.bet}원"
            elif self.player1_roll < self.player2_roll:
                point_manager.add_point(p1_id, -self.bet)
                point_manager.add_point(p2_id, self.bet)
                result = f"🏆 {p2_user.mention} 승리! +{self.bet}원"
            else:
                result = "🤝 무승부! 포인트 변동 없음."

            button.disabled = True
            await msg.edit(
                content=(
                    f"{self.player1.mention} 🎲: {DICE_EMOJIS[self.player1_roll]}\n"
                    f"{p2_user.mention} 🎲: {DICE_EMOJIS[self.player2_roll]}\n"
                    f"{result}"
                ),
                view=self
            )
            self.stop()


# ✅ /주사위 명령어
@app_commands.command(name="주사위", description="주사위 게임을 플레이합니다.")
@app_commands.describe(
    모드="싱글 또는 멀티 선택",
    배팅="배팅 안할시 기본 10원만 배팅됨. 배팅할 포인트 (1~1000)",
    상대방="(선택 사항) 상대 유저 (멀티 모드)"
)
async def dice_command(
    interaction: discord.Interaction,
    모드: Literal["싱글", "멀티"],
    배팅: int = 10,
    상대방: Optional[discord.User] = None
):
    uid = str(interaction.user.id)

    if not point_manager.is_registered(uid):
        return await interaction.response.send_message("❗ 먼저 `/등록`을 해주세요.", ephemeral=True)

    if 배팅 < 1:
        return await interaction.response.send_message("❗ 배팅 포인트는 최소 1 이상이어야 합니다.", ephemeral=True)

    if 모드 == "싱글":
        await interaction.response.send_message(
            f"🎮 싱글 주사위 게임 시작! 배팅: {배팅}원\n{interaction.user.mention}님, 버튼을 눌러 주세요!",
            view=SingleDiceView(interaction.user, 배팅)
        )
    else:
        if 상대방:
            if 상대방.id == interaction.user.id:
                return await interaction.response.send_message("❗ 자신과는 게임할 수 없습니다.", ephemeral=True)
            if not point_manager.is_registered(str(상대방.id)):
                return await interaction.response.send_message("❗ 상대방이 등록되어 있지 않습니다.", ephemeral=True)

        await interaction.response.send_message(
            f"🎮 멀티 주사위 게임 시작! 배팅: {배팅}원\n{상대방.mention if 상대방 else '누구나'} 참여 가능!",
            view=MultiDiceView(interaction.user, 배팅, opponent=상대방)
        )
# help_command.py
import discord
from discord import app_commands

class HelpCategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="📌 포인트 시스템", style=discord.ButtonStyle.primary)
    async def point_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="📌 포인트 시스템 도움말", color=discord.Color.blue())
        embed.add_field(name="/등록", value="플레이어 등록을 해야만 게임을 하실 수 있습니다.", inline=False)
        embed.add_field(name="/잔액", value="가지고 있는 현금을 확인 할 수 있습니다.", inline=False)
        embed.add_field(name="/조회", value="플레이어들의 현금을 조회 가능 합니다.", inline=False)
        embed.add_field(name="/돈", value="내 현금과 전체 순위를 볼 수 있습니다.", inline=False)
        embed.add_field(name="/현금선물", value="다른 플레이어에게 지급할 수 있습니다.", inline=False)
        embed.add_field(name="/현금순위", value="TOP 10 현황을 볼 수 있습니다.", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🎮 게임 명령어", style=discord.ButtonStyle.success)
    async def game_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🎮 게임 도움말", color=discord.Color.green())
        embed.add_field(name="/가위바위보", value="가위바위보 게임", inline=False)
        embed.add_field(name="/주사위게임", value="숫자가 높은 쪽이 이기는 게임", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🛠 관리자 전용", style=discord.ButtonStyle.danger)
    async def admin_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("⚠️ 관리자만 볼 수 있습니다.", ephemeral=True)
            return

        embed = discord.Embed(title="🛠 관리자 명령어", color=discord.Color.red())
        embed.add_field(name="/현금지급", value="현금 지급 할 수 있음.", inline=False)
        embed.add_field(name="/현금수거", value="현금을 빼앗을 수 있음.", inline=False)
        embed.add_field(name="/등록목록", value="등록된 사람들의 정보를 볼 수 있음.", inline=False)
        embed.add_field(name="/탈퇴", value="등록된 사람들의 정보를 지울 수 있음.", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@app_commands.command(name="도움말", description="카테고리별 도움말을 확인합니다.")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 도움말 메뉴",
        description="아래 버튼을 눌러 도움말을 확인하세요!",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed, view=HelpCategoryView(), ephemeral=True)

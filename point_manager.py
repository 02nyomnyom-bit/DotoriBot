import os
import json
import datetime
import discord
from discord import app_commands, Interaction, Member

#경로 설정
DATA_DIR = "data"
LOG_DIR = "logs"
POINTS_FILE = os.path.join(DATA_DIR, "points.json")
GIFT_TRACK_FILE = os.path.join(DATA_DIR, "gift_track.json")
LOG_FILE = os.path.join(LOG_DIR, "point_log.txt")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

#유틸 
def now_str():
    return datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

def log_action(msg: str):
    log = f"{now_str()} {msg}"
    print(log)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log + "\n")

def load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

async def send_response(interaction, content, only_me=False):
    await interaction.response.send_message(content, ephemeral=only_me)

def require_registration(user_id: str):
    return user_id in load_points()

#포인트 로직
def load_points():
    return load_json(POINTS_FILE)

def save_points(data):
    save_json(data, POINTS_FILE)

def get_point(user_id: str):
    return load_points().get(user_id, 0)

def add_point(user_id: str, amount: int):
    points = load_points()
    current = points.get(user_id, 0)
    points[user_id] = max(0, current + amount)
    save_points(points)

def set_point(user_id: str, amount: int):
    points = load_points()
    points[user_id] = max(0, amount)
    save_points(points)

def is_registered(user_id: str):
    return user_id in load_points()

def register_user(user_id: str):
    if not is_registered(user_id):
        add_point(user_id, 0)
        log_action(f"✅ 등록됨: {user_id}")
        return True
    return False

def get_gift_count_today(user_id: str):
    gift_data = load_json(GIFT_TRACK_FILE)
    today = datetime.date.today().isoformat()
    return gift_data.get(f"{user_id}_{today}", 0)

def increment_gift_count(user_id: str):
    gift_data = load_json(GIFT_TRACK_FILE)
    today = datetime.date.today().isoformat()
    key = f"{user_id}_{today}"
    gift_data[key] = gift_data.get(key, 0) + 1
    save_json(gift_data, GIFT_TRACK_FILE)
    return gift_data[key]



#명령어

@app_commands.command(name="등록", description="Gamble의 플레이어 등록 신청합니다.")
async def register_command(interaction: Interaction):
    user_id = str(interaction.user.id)
    if is_registered(user_id):
        await send_response(interaction, "이미 등록된 플레이어입니다.")
    else:
        register_user(user_id)
        await send_response(interaction, "Gamble의 플레이어가 되었습니다. 현금 : 0원")

@app_commands.command(name="잔액", description="내 현금을 확인합니다.")
async def point_command(interaction: Interaction):
    user_id = str(interaction.user.id)
    if not is_registered(user_id):
        return await send_response(interaction, "⚠️ 먼저 `/등록` 명령어로 등록해주세요.")

    point = get_point(user_id)
    await send_response(interaction, f"💰 {interaction.user.mention}님의 가진 돈: {point}원", only_me=False)

@app_commands.command(name="조회", description="플레이어의 현금을 조회합니다.")
@app_commands.describe(대상="현금을 확인할 유저")
async def point_check(interaction: Interaction, 대상: discord.Member):
    user_id = str(대상.id)
    if not is_registered(user_id):
        return await send_response(interaction, f"{대상.mention}님은 아직 등록되지 않았습니다.")

    point = get_point(user_id)
    await send_response(interaction, f"🔎 {대상.mention}님의 가진 돈: {point}원", only_me=False)

@app_commands.command(name="현금지급", description="플레이어에게 현금을 지급합니다. (관리자 전용)")
@app_commands.describe(대상="현금을 지급 할 유저", 원="추가할 현금")
async def add_point_admin(interaction: Interaction, 대상: discord.Member, 원: int):
    if not interaction.user.guild_permissions.administrator:
        return await send_response(interaction, "🚫 관리자만 사용할 수 있습니다.")

    user_id = str(대상.id)
    register_user(user_id)
    add_point(user_id, 원)
    log_action(f"[추가] {interaction.user} → {대상} : +{원}원")
    await send_response(interaction, f"✅ {대상.mention}님에게 {원}원을 지급했습니다!", only_me=False)

@app_commands.command(name="현금수거", description="사용자의 현금을 수거합니다. (관리자 전용)")
@app_commands.describe(대상="현금을 수거 할 유저", 원="수거 할 현금")
async def subtract_point_admin(interaction: Interaction, 대상: discord.Member, 원: int):
    if not interaction.user.guild_permissions.administrator:
        return await send_response(interaction, "🚫 관리자만 사용할 수 있습니다.")

    user_id = str(대상.id)
    register_user(user_id)
    prev = get_point(user_id)
    actual = min(prev, 원)
    add_point(user_id, -actual)
    log_action(f"[차감] {interaction.user} → {대상} : -{actual}원")
    await send_response(interaction, f"✅ {대상.mention}님의 현금을 {actual}원 수거했습니다!", only_me=False)

@app_commands.command(name="현금선물", description="다른 플레이어에게 현금을 선물합니다. (하루 3회)")
@app_commands.describe(받는사람="선물할 플레이어", 원="선물할 현금")
async def gift_point(interaction: Interaction, 받는사람: discord.Member, 원: int):
    sender_id = str(interaction.user.id)
    receiver_id = str(받는사람.id)

    if sender_id == receiver_id:
        return await send_response(interaction, "❌ 자신에게는 돈을 선물할 수 없습니다.")

    if not is_registered(sender_id) or not is_registered(receiver_id):
        return await send_response(interaction, "⚠️ 선물하려면 두 플레이어 모두 등록되어 있어야 합니다.")

    gift_data = load_json(GIFT_TRACK_FILE)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    daily_key = f"{sender_id}_{today}"
    gift_count = gift_data.get(daily_key, 0)

    if gift_count >= 3:
        return await send_response(interaction, "❌ 오늘의 선물 횟수를 모두 사용했습니다. (하루 최대 3회)")

    if get_point(sender_id) < 원:
        return await send_response(interaction, f"❌ 돈이 부족합니다. 현재 보유: {get_point(sender_id)}원")

    add_point(sender_id, -원)
    add_point(receiver_id, 원)
    gift_data[daily_key] = gift_count + 1
    save_json(gift_data, GIFT_TRACK_FILE)

    log_action(f"[선물] {interaction.user} → {받는사람} : {원}원 (오늘 {gift_data[daily_key]}회)")
    await send_response(
        interaction,
        f"🎁 {interaction.user.mention}님이 {받는사람.mention}님에게 {원}원을 돈을 선물했습니다! (오늘 {gift_data[daily_key]}/3회)",
        only_me=False
    )

@app_commands.command(name="현금순위", description="상위 10명 랭킹을 확인합니다.")
async def point_leaderboard(interaction: Interaction):
    points = load_points()
    if not points:
        return await send_response(interaction, "등록된 플레이어가 없습니다.")

    sorted_users = sorted(points.items(), key=lambda x: x[1], reverse=True)
    msg = "🏆 **순위 TOP 10**\n"
    for rank, (user_id, point) in enumerate(sorted_users[:10], 1):
        try:
            user = await interaction.guild.fetch_member(int(user_id))
            name = user.display_name if user else f"유저 {user_id}"
        except:
            name = f"유저 {user_id}"
        msg += f"{rank}. {name} - {point}원\n"

    await send_response(interaction, msg, only_me=False)

@app_commands.command(name="돈", description="내 현금과 전체 순위를 확인합니다.")
async def my_point_and_rank(interaction: Interaction):
    user_id = str(interaction.user.id)
    if not is_registered(user_id):
        return await send_response(interaction, "⚠️ 먼저 `/등록` 명령어로 등록해주세요.")

    all_points = load_points()
    sorted_users = sorted(all_points.items(), key=lambda x: x[1], reverse=True)
    rank = next((i + 1 for i, (uid, _) in enumerate(sorted_users) if uid == user_id), None)
    point = all_points.get(user_id, 0)

    await send_response(
        interaction,
        f"📊 {interaction.user.mention}님이 가진 돈: **{point}원**\n"
        f"🏅 전체 순위: {rank}위",
        only_me=False
    )

@app_commands.command(name="등록목록", description="등록된 플레이어 목록을 확인합니다. (관리자 전용)")
async def list_registered_users(interaction: Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await send_response(interaction, "🚫 관리자만 사용할 수 있습니다.")

    all_points = load_points()
    if not all_points:
        return await send_response(interaction, "❗ 등록된 사용자가 없습니다.", only_me=True)

    msg = "📋 등록된 플레이어 목록:\n"
    for user_id in all_points:
        try:
            member = await interaction.guild.fetch_member(int(user_id))
            name = member.display_name if member else f"(탈퇴 유저)"
        except:
            name = "(탈퇴 유저)"
        msg += f"- {name} ({user_id})\n"

    await send_response(interaction, msg[:2000], only_me=True)

@app_commands.command(name="탈퇴", description="특정 사용자를 탈퇴시킵니다. (관리자 전용)")
@app_commands.describe(대상="탈퇴 시킬 플레이어")
async def unregister_user(interaction: Interaction, 대상: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        return await send_response(interaction, "🚫 관리자만 사용할 수 있습니다.")

    user_id = str(대상.id)
    points = load_points()

    if user_id not in points:
        return await send_response(interaction, f"{대상.mention}님은 등록된 플레이어가 아닙니다.", only_me=True)

    del points[user_id]
    save_points(points)

    log_action(f"❌ 등록 해제됨: {대상} ({user_id}) by {interaction.user}")
    await send_response(interaction, f"✅ {대상.mention}님을 목록에서 제거했습니다.", only_me=True)
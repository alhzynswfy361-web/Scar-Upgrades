# =========================================================
# PROFESSIONAL DISCORD RANK SYSTEM
# discord.py 2.x
# =========================================================

import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from datetime import datetime
import os

# =========================================================
# CONFIG
# =========================================================

# ID رول بداية قسم الرتب
START_ROLE_ID = 1500811581603446865

# ID رول نهاية قسم الرتب
END_ROLE_ID = 1500811245589368933

# ID روم اللوق
LOG_CHANNEL_ID = 1504899463058292889

# الأونرات المسموح لهم
ALLOWED_OWNERS = [
    1434126282429304914,
    955474041240707152,
    1098217662309470318,
    1201869496550162495,
    920881009598267402
]

# =========================================================
# DATABASE
# =========================================================

db = sqlite3.connect("ranks.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    moderator_id INTEGER,
    action TEXT,
    old_rank TEXT,
    new_rank TEXT,
    amount INTEGER,
    reason TEXT,
    time TEXT
)
""")

db.commit()

# =========================================================
# BOT
# =========================================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="+",
    intents=intents
)

# =========================================================
# FUNCTIONS
# =========================================================

def get_rank_roles(guild):

    start_role = guild.get_role(START_ROLE_ID)
    end_role = guild.get_role(END_ROLE_ID)

    if not start_role or not end_role:
        return []

    start_pos = start_role.position
    end_pos = end_role.position

    low = min(start_pos, end_pos)
    high = max(start_pos, end_pos)

    rank_roles = []

    for role in guild.roles:

        if role.is_default():
            continue

        if role.id == START_ROLE_ID:
            continue

        if role.id == END_ROLE_ID:
            continue

        if low < role.position < high:
            rank_roles.append(role)

    rank_roles.sort(key=lambda r: r.position)

    return rank_roles


def get_member_rank(member, rank_roles):

    member_ranks = [r for r in member.roles if r in rank_roles]

    if not member_ranks:
        return None

    return max(member_ranks, key=lambda r: r.position)


async def save_log(
    user_id,
    moderator_id,
    action,
    old_rank,
    new_rank,
    amount,
    reason
):

    cursor.execute("""
    INSERT INTO logs (
        user_id,
        moderator_id,
        action,
        old_rank,
        new_rank,
        amount,
        reason,
        time
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        moderator_id,
        action,
        old_rank,
        new_rank,
        amount,
        reason,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    db.commit()

# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    print(f"✅ Logged in as {bot.user}")

    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands")

    except Exception as e:
        print(e)

# =========================================================
# PROMOTE
# =========================================================

@bot.tree.command(
    name="promote",
    description="ترقية عضو"
)

@app_commands.describe(
    member="العضو",
    amount="عدد الرتب",
    reason="سبب الترقية"
)

async def promote(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: int,
    reason: str
):

    if interaction.user.id not in ALLOWED_OWNERS:

        return await interaction.response.send_message(
            "❌ ليس لديك صلاحية.",
            ephemeral=True
        )

    rank_roles = get_rank_roles(interaction.guild)

    if not rank_roles:

        return await interaction.response.send_message(
            "❌ لم يتم العثور على الرتب.",
            ephemeral=True
        )

    current_rank = get_member_rank(member, rank_roles)

    if not current_rank:

        return await interaction.response.send_message(
            "❌ العضو لا يملك رتبة داخل قسم الرتب.",
            ephemeral=True
        )

    current_index = rank_roles.index(current_rank)

    new_index = min(
        current_index + amount,
        len(rank_roles) - 1
    )

    new_rank = rank_roles[new_index]

    if current_rank == new_rank:

        return await interaction.response.send_message(
            "❌ لا يمكن ترقية العضو أكثر.",
            ephemeral=True
        )

    await member.remove_roles(current_rank)
    await member.add_roles(new_rank)

    embed = discord.Embed(
        title="🟢 تمت الترقية",
        color=discord.Color.green()
    )

    embed.add_field(
        name="العضو",
        value=member.mention,
        inline=False
    )

    embed.add_field(
        name="من",
        value=current_rank.name,
        inline=True
    )

    embed.add_field(
        name="إلى",
        value=new_rank.name,
        inline=True
    )

    embed.add_field(
        name="عدد الرتب",
        value=f"+{amount}",
        inline=False
    )

    embed.add_field(
        name="السبب",
        value=reason,
        inline=False
    )

    embed.add_field(
        name="بواسطة",
        value=interaction.user.mention,
        inline=False
    )

    embed.set_footer(
        text=datetime.now().strftime("%Y-%m-%d %H:%M")
    )

    await interaction.response.send_message(embed=embed)

    log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)

    if log_channel:
        await log_channel.send(embed=embed)

    await save_log(
        member.id,
        interaction.user.id,
        "promote",
        current_rank.name,
        new_rank.name,
        amount,
        reason
    )

# =========================================================
# DEMOTE
# =========================================================

@bot.tree.command(
    name="demote",
    description="تخفيض عضو"
)

@app_commands.describe(
    member="العضو",
    amount="عدد الرتب",
    reason="سبب التخفيض"
)

async def demote(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: int,
    reason: str
):

    if interaction.user.id not in ALLOWED_OWNERS:

        return await interaction.response.send_message(
            "❌ ليس لديك صلاحية.",
            ephemeral=True
        )

    rank_roles = get_rank_roles(interaction.guild)

    if not rank_roles:

        return await interaction.response.send_message(
            "❌ لم يتم العثور على الرتب.",
            ephemeral=True
        )

    current_rank = get_member_rank(member, rank_roles)

    if not current_rank:

        return await interaction.response.send_message(
            "❌ العضو لا يملك رتبة داخل قسم الرتب.",
            ephemeral=True
        )

    current_index = rank_roles.index(current_rank)

    new_index = max(
        current_index - amount,
        0
    )

    new_rank = rank_roles[new_index]

    if current_rank == new_rank:

        return await interaction.response.send_message(
            "❌ لا يمكن تخفيض العضو أكثر.",
            ephemeral=True
        )

    await member.remove_roles(current_rank)
    await member.add_roles(new_rank)

    embed = discord.Embed(
        title="🔴 تم التخفيض",
        color=discord.Color.red()
    )

    embed.add_field(
        name="العضو",
        value=member.mention,
        inline=False
    )

    embed.add_field(
        name="من",
        value=current_rank.name,
        inline=True
    )

    embed.add_field(
        name="إلى",
        value=new_rank.name,
        inline=True
    )

    embed.add_field(
        name="عدد الرتب",
        value=f"-{amount}",
        inline=False
    )

    embed.add_field(
        name="السبب",
        value=reason,
        inline=False
    )

    embed.add_field(
        name="بواسطة",
        value=interaction.user.mention,
        inline=False
    )

    embed.set_footer(
        text=datetime.now().strftime("%Y-%m-%d %H:%M")
    )

    await interaction.response.send_message(embed=embed)

    log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)

    if log_channel:
        await log_channel.send(embed=embed)

    await save_log(
        member.id,
        interaction.user.id,
        "demote",
        current_rank.name,
        new_rank.name,
        amount,
        reason
    )

# =========================================================
# CHECK
# =========================================================

@bot.tree.command(
    name="check",
    description="فحص عضو"
)

@app_commands.describe(
    member="العضو"
)

async def check(
    interaction: discord.Interaction,
    member: discord.Member
):

    rank_roles = get_rank_roles(interaction.guild)

    current_rank = get_member_rank(member, rank_roles)

    cursor.execute("""
    SELECT action, old_rank, new_rank, amount, reason, time
    FROM logs
    WHERE user_id = ?
    ORDER BY id DESC
    LIMIT 10
    """, (member.id,))

    logs = cursor.fetchall()

    embed = discord.Embed(
        title="📋 معلومات العضو",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="العضو",
        value=member.mention,
        inline=False
    )

    embed.add_field(
        name="الرتبة الحالية",
        value=current_rank.name if current_rank else "لا يوجد",
        inline=False
    )

    if logs:

        text = ""

        for log in logs:

            action = "🟢 ترقية" if log[0] == "promote" else "🔴 تخفيض"

            text += (
                f"{action}\n"
                f"{log[1]} ➜ {log[2]}\n"
                f"العدد: {log[3]}\n"
                f"السبب: {log[4]}\n"
                f"{log[5]}\n\n"
            )

        embed.add_field(
            name="آخر العمليات",
            value=text[:1024],
            inline=False
        )

    await interaction.response.send_message(embed=embed)

# =========================================================
# OWNERS
# =========================================================

@bot.tree.command(
    name="owners",
    description="عرض الأونرات"
)

async def owners(interaction: discord.Interaction):

    text = ""

    for owner_id in ALLOWED_OWNERS:

        try:
            user = await bot.fetch_user(owner_id)
            text += f"• {user.mention}\n"

        except:
            pass

    embed = discord.Embed(
        title="👑 الأونرات",
        description=text if text else "لا يوجد",
        color=discord.Color.gold()
    )

    await interaction.response.send_message(embed=embed)

# =========================================================
# RUN
# =========================================================

bot.run(os.getenv("TOKEN"))

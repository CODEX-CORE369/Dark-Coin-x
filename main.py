import asyncio
import os
import re
import time
import requests
import unicodedata
import io
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask
from pymongo import MongoClient
from pyrogram import Client, filters, enums
from pyrogram.types import Message, ChatMemberUpdated

# --- CONFIGURATION ---
API_ID = 20579940
API_HASH = "6fc0ea1c8dacae05751591adedc177d7"
BOT_TOKEN = "8513850569:AAHCsKyy1nWTYVKH_MtbW8IhKyOckWLTEDA"
B = "ᴅx"
OWNER_ID = 6703335929

# Multiple allowed group usernames can be added here
ALLOWED_GROUP_USERNAMES = ["Dark_Zone_x", "DARK_GANG369", "Dark_gang_x", "dark_lady_369"]

# --- DATABASE ---
MONGO_URL = "mongodb+srv://shadowur6_db_user:8AIIxZUjpanaQBjh@dx-codex.fmqcovu.mongodb.net/?retryWrites=true&w=majority&appName=Dx-codex"
client_db = MongoClient(MONGO_URL, connectTimeoutMS=30000, connect=False)
db = client_db["DX_COIN_DB"]
users_col = db["users"]

# --- WEB SERVER ---
web = Flask('')
@web.route('/')
def home(): return f"{B} sʏsᴛᴇᴍ ᴏɴʟɪɴᴇ"

def run_web():
    port = int(os.environ.get('PORT', 8080))
    web.run(host='0.0.0.0', port=port)

# --- BOT CLIENT ---
app = Client("DX_COIN_V3", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
INIT_SUDO = [6366113192, 6703335929, 6737589257]

# --- HELPERS ---
def keep_alive_ping():
    # Modified to support Render external URL dynamically
    port = int(os.environ.get('PORT', 8080))
    URL = os.environ.get('RENDER_EXTERNAL_URL', f"http://localhost:{port}")
    
    while True:
        try:
            requests.get(URL)
            print(f"[{B}] Pinging server ({URL}) to stay awake...")
        except Exception as e:
            print(f"[{B}] Ping failed: {e}")
        time.sleep(300)

async def check_sudo(user_id):
    if user_id in INIT_SUDO or user_id == OWNER_ID: return True
    user = users_col.find_one({"user_id": user_id})
    return user.get("is_sudo", 0) == 1 if user else False

def get_mention(user_id, name):
    name = re.sub(r'[<>#]', '', str(name)) if name else "Usᴇʀ"
    return f"<a href='tg://user?id={user_id}'>{name[:15]}</a>"

def get_rank_info(coins):
    if coins >= 400: return ("💎", "💎💎💎", "ᴄᴏᴅᴇ ᴏᴡɴᴇʀ")
    elif coins >= 200: return ("🌟🌟🌟", "⭐⭐⭐", "ᴀᴅ/ʀᴜʟᴇʀ")
    elif coins >= 100: return ("🌟🌟", "⭐⭐", "ʜ-ᴄᴀᴘᴛᴀɪɴ")
    elif coins >= 50: return ("🌟", "⭐", "ᴅᴇs-ɴᴀᴍᴇ")
    return ("⚪️", "🌑", "ᴍᴇᴍʙᴇʀ")

# Advanced Rank Algorithm (Points based - Lower rank_score is better)
def get_rank_deduction(amount):
    if amount == 20: return 10
    elif amount == 10: return 5
    elif amount == 5: return 3
    elif amount == 1: return 1
    else: return max(1, amount // 2)

def update_user_rank(user_id, amount_added):
    user = users_col.find_one({"user_id": user_id})
    if not user: return
    current_rank = user.get("rank_score", 1000)
    deduction = get_rank_deduction(amount_added)
    
    # 1 is the absolute highest rank mathematically, cannot go lower
    new_rank = max(1, current_rank - deduction)
    users_col.update_one({"user_id": user_id}, {"$set": {"rank_score": new_rank}})

def sync_data(user):
    if not user: return
    now = time.time()
    users_col.update_one(
        {"user_id": user.id},
        {"$set": {"full_name": f"{user.first_name} {user.last_name or ''}".strip(), "username": user.username},
         "$setOnInsert": {
             "coins": 0, 
             "vault": 0, 
             "last_claim": 0, 
             "is_sudo": 0,
             "deducted_50": 0,
             "is_banned": 0,
             "rank_score": 1000,           # New rank score base
             "vault_last_calc": now        # To track 7-day passive income
         }},
        upsert=True
    )

async def del_cmd(message):
    try: await message.delete()
    except: pass

async def get_target_user(client, message, parts):
    if message.reply_to_message: 
        return message.reply_to_message.from_user
    if len(parts) > 1:
        u_input = parts[1]
        if u_input.isdigit(): 
            try: return await client.get_users(int(u_input))
            except: pass
        if u_input.startswith("@"):
            try: return await client.get_users(u_input)
            except: pass
        if len(parts) > 2:
            u_input_2 = parts[2]
            if u_input_2.isdigit() or u_input_2.startswith("@"):
                try: return await client.get_users(u_input_2)
                except: pass
    return None

# Expanded Leet Speak and visual substitute mapping
CHARACTER_MAP = {
    '0': 'o', '4': 'a', '@': 'a', '8': 'b', '3': 'e', '1': 'i', '!': 'i', 
    '$': 's', '7': 't', '(': 'c', '[': 'c', '{': 'c', '©': 'c', 
    'v': 'v', '×': 'x', 'к': 'k', 'ʀ': 'r', '∆': 'a', 'Λ': 'a', 
    'ß': 'b', '€': 'e', '£': 'e', '#': 'h', '®': 'r', '5': 's', 
    '+': 't', 'µ': 'u', '¥': 'y'
}

# Multi-character substitutions
MULTI_CHAR_MAP = {
    'cl': 'd', '|)': 'd', '|>': 'd', '|-|': 'h', '|=': 'f'
}

def advanced_cleaner(text):
    """
    Ultra-advanced cleaning algorithm: Handles Regional Indicators (Flags), 
    Mathematical Alphanumeric fonts, Leet Speak, Zalgo, and hidden characters.
    """
    if not text:
        return ""
    
    # 1. Handle Regional Indicators (e.g., 🇩, 🇦)
    # Convert flag-like letters to standard lowercase letters a-z
    cleaned_chars = []
    for char in text:
        code = ord(char)
        if 127462 <= code <= 127487:  # Unicode range for regional indicators
            cleaned_chars.append(chr(code - 127462 + 97))
        else:
            cleaned_chars.append(char)
    text = ''.join(cleaned_chars)
    
    # 2. Normalize stylized fonts (NFKC converts 𝐀𝐑𝐊 to ARK) and lowercase
    text = unicodedata.normalize('NFKC', text).lower()
    
    # 3. Apply Multi-character Leet Speak replacements
    for k, v in MULTI_CHAR_MAP.items():
        text = text.replace(k, v)
        
    # 4. Apply Single-character Leet Speak mapping
    for char, replacement in CHARACTER_MAP.items():
        text = text.replace(char, replacement)
        
    # 5. Strip Diacritics/Glitch marks (Zalgo text)
    text = ''.join(
        c for c in unicodedata.normalize('NFD', text) 
        if unicodedata.category(c) != 'Mn'
    )
    
    # 6. Regex: Remove EVERYTHING except basic lowercase letters (a-z)
    # This collapses strings like "d.a.r.k", "g_r_e_y", or "d a r k" into a single solid word
    clean_text = re.sub(r'[^a-z]', '', text)
    
    return clean_text

def is_dark_user(user):
    """
    Checks if the word 'dark' OR 'grey' exists anywhere in the user's identity 
    after passing through the ultra-advanced cleaning algorithm.
    """
    # Combine first name, last name, and username for a full identity scan
    identity_string = f"{user.first_name or ''} {user.last_name or ''} {user.username or ''}"
    
    # Process the identity through the advanced cleaner
    clean_identity = advanced_cleaner(identity_string)
    
    # Final check for the keywords
    return "dark" in clean_identity or "grey" in clean_identity

# --- MILESTONE LOGIC ---
async def handle_coin_update(client, chat_id, user, amt_added):
    if amt_added <= 0: return # Block negative bugs completely
    
    user_id = user.id
    user_db = users_col.find_one({"user_id": user_id})
    if not user_db: return

    old_coins = user_db.get("coins", 0)
    deducted_flag = user_db.get("deducted_50", 0)
    
    new_coins_temp = old_coins + amt_added
    
    # 1. Check for 1000 Coin Auto-Reset (New Algorithm)
    if new_coins_temp >= 1000:
        users_col.update_one(
            {"user_id": user_id},
            {"$set": {"coins": 10, "rank_score": 1000}} # Resets to 10
        )
        try:
            m = get_mention(user_id, user.first_name)
            msg = (
                f"<b>┏━━「 🔄 ᴀᴄᴄᴏᴜɴᴛ ʀᴇsᴇᴛ 」━━┓</b>\n"
                f"<b>┃ 👤 ᴜsᴇʀ: {m}</b>\n"
                f"<b>┃ ⚠️ ɪɴғᴏ: 1000 ᴄᴏɪɴs ʀᴇᴀᴄʜᴇᴅ!</b>\n"
                f"<b>┃ 🔄 ᴀᴄᴛɪᴏɴ: ᴀᴄᴄᴏᴜɴᴛ ʀᴇsᴇᴛ ᴛᴏ 10 ᴄᴏɪɴs</b>\n"
                f"<b>┗━━━━━━━━━━━━━━━━━━┛</b>"
            )
            sent = await client.send_message(chat_id, msg)
            await sent.pin(both_sides=True)
        except: pass
        return

    # Update dynamic rank based on amount added
    update_user_rank(user_id, amt_added)

    # 2. Check for 50 Coin Milestone
    if deducted_flag == 0 and new_coins_temp >= 50:
        final_coins = new_coins_temp - 50
        users_col.update_one(
            {"user_id": user_id},
            {"$set": {"coins": final_coins, "deducted_50": 1}}
        )
        m = get_mention(user_id, user.first_name)
        msg = (
            f"<b>┏━━「 🎉 ᴄᴏɴɢʀᴀᴛᴜʟᴀᴛɪᴏɴs 」━━┓</b>\n"
            f"<b>┃ 👤 ᴜsᴇʀ: {m}</b>\n"
            f"<b>┃ 🏆 ᴀᴄʜɪᴇᴠᴇᴍᴇɴᴛ: sᴛᴀʀ ᴜɴʟᴏᴄᴋᴇᴅ!</b>\n"
            f"<b>┃ 📉 sʏsᴛᴇᴍ: 50 ᴄᴏɪɴs ᴅᴇᴅᴜᴄᴛᴇᴅ</b>\n"
            f"<b>┃ ✨ sᴛᴀᴛᴜs: ᴏғғɪᴄɪᴀʟ sᴛᴀʀ ʟɪsᴛ</b>\n"
            f"<b>┗━━━━━━━━━━━━━━━━━━┛</b>"
        )
        try:
            sent = await client.send_message(chat_id, msg)
            await sent.pin(both_sides=True)
        except: pass
        return
        
    else:
        users_col.update_one({"user_id": user_id}, {"$set": {"coins": new_coins_temp}})
        final_coins = new_coins_temp

    # 3. Check for Rank Ups
    old_badge, _, _ = get_rank_info(old_coins)
    new_badge, stars, r_name = get_rank_info(final_coins)

    if new_badge != old_badge and final_coins > old_coins:
        if final_coins >= 100: 
            m = get_mention(user_id, user.first_name)
            msg = (
                f"<b>┏━━「 🌟 ʟᴇᴠᴇʟ ᴜᴘ 」━━┓</b>\n"
                f"<b>┃ 👤 ᴜsᴇʀ: {m}</b>\n"
                f"<b>┃ 🎖️ ɴᴇᴡ ʀᴀɴᴋ: {new_badge}</b>\n"
                f"<b>┃ 👔 ᴛɪᴛʟᴇ: {r_name}</b>\n"
                f"<b>┗━━━━━━━━━━━━━━┛</b>"
            )
            try:
                sent = await client.send_message(chat_id, msg)
                await sent.pin(both_sides=True)
            except: pass

# --- GROUP RESTRICTION ---
@app.on_message(filters.group, group=-2)
async def check_group(client, message):
    if message.chat.username not in ALLOWED_GROUP_USERNAMES:
        try:
            groups_str = ", ".join([f"@{g}" for g in ALLOWED_GROUP_USERNAMES])
            await message.reply(
                f"<b>┏━━「 🚫 ʟᴇᴀᴠɪɴɢ 」━━┓</b>\n"
                f"<b>┃ ⚠️ ᴀʟᴇʀᴛ: ᴡʀᴏɴɢ ᴢᴏɴᴇ</b>\n"
                f"<b>┃ 🛡️ ᴏɴʟʏ ғᴏʀ: {groups_str[:25]}...</b>\n"
                f"<b>┗━━━━━━━━━━━━━━┛</b>"
            )
            await client.leave_chat(message.chat.id)
        except: pass

# --- BAN CHECK ---
@app.on_message(filters.command(["claim", "gift", "coin", "vault"]) & filters.group, group=-1)
async def ban_filter(client, message):
    sync_data(message.from_user)
    user = users_col.find_one({"user_id": message.from_user.id})
    if user and user.get("is_banned", 0) == 1:
        await del_cmd(message)
        m = get_mention(message.from_user.id, message.from_user.first_name)
        await message.reply(
            f"<b>┏━━「 🚫 ʙᴀɴɴᴇᴅ 」━━┓</b>\n"
            f"<b>┃ 👤 ᴜsᴇʀ: {m}</b>\n"
            f"<b>┃ ⚠️ sᴛᴀᴛᴜs: ʀᴇsᴛʀɪᴄᴛᴇᴅ</b>\n"
            f"<b>┃ ❌ ᴀᴄᴛɪᴏɴ: ᴅᴇɴɪᴇᴅ</b>\n"
            f"<b>┗━━━━━━━━━━━━━━┛</b>"
        )
        message.stop_propagation()

# --- ADMIN COMMANDS ---
@app.on_message(filters.command(["acoin", "mcoin"]))
async def manage_coin(client, message):
    if not await check_sudo(message.from_user.id): 
        return await del_cmd(message)
    
    cmd = message.command[0]
    parts = message.text.split()
    target = await get_target_user(client, message, parts)
    
    amount = 0
    for p in parts:
        # Avoid bugs by checking if it contains digits or minus sign
        if p.isdigit() or (p.startswith("-") and p[1:].isdigit()):
            amount = abs(int(p)) # Force positive integer reading
            break
            
    m_admin = get_mention(message.from_user.id, message.from_user.first_name)
    
    if not target: return await message.reply(f"<b>⚠️ {m_admin}, ᴜsᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ!</b>")
    if amount == 0: return await message.reply(f"<b>⚠️ {m_admin}, ᴇɴᴛᴇʀ ᴀᴍᴏᴜɴᴛ!</b>")

    sync_data(target)
    
    if cmd == "acoin":
        await handle_coin_update(client, message.chat.id, target, amount)
        u_data = users_col.find_one({"user_id": target.id})
        await message.reply(
            f"<b>┏━━「 ✅ ᴀᴅᴅᴇᴅ 」━━┓</b>\n"
            f"<b>┃ 👤 ᴀᴅᴍɪɴ: {m_admin}</b>\n"
            f"<b>┃ 👤 ᴜsᴇʀ: {get_mention(target.id, target.first_name)}</b>\n"
            f"<b>┃ 💰 ᴀᴍᴏᴜɴᴛ: +{amount}</b>\n"
            f"<b>┃ 👜 ɴᴏᴡ: {u_data['coins']}</b>\n"
            f"<b>┗━━━━━━━━━━━━━━┛</b>"
        )
        
    elif cmd == "mcoin":
        u_data = users_col.find_one({"user_id": target.id})
        # Prevent going below zero
        if u_data['coins'] < amount: amount = u_data['coins'] 
        
        users_col.update_one({"user_id": target.id}, {"$inc": {"coins": -amount}})
        u_data = users_col.find_one({"user_id": target.id})
        await message.reply(
            f"<b>┏━━「 🔻 ʀᴇᴍᴏᴠᴇᴅ 」━━┓</b>\n"
            f"<b>┃ 👤 ᴀᴅᴍɪɴ: {m_admin}</b>\n"
            f"<b>┃ 👤 ᴜsᴇʀ: {get_mention(target.id, target.first_name)}</b>\n"
            f"<b>┃ 💰 ᴀᴍᴏᴜɴᴛ: -{amount}</b>\n"
            f"<b>┃ 👜 ɴᴏᴡ: {u_data['coins']}</b>\n"
            f"<b>┗━━━━━━━━━━━━━━┛</b>"
        )

# NEW: Admin Manual Reset Command
@app.on_message(filters.command("reset"))
async def reset_user(client, message):
    if not await check_sudo(message.from_user.id): 
        return await del_cmd(message)
    
    parts = message.text.split()
    target = await get_target_user(client, message, parts)
    m_admin = get_mention(message.from_user.id, message.from_user.first_name)

    if not target: 
        return await message.reply(f"<b>⚠️ {m_admin}, ᴜsᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ!</b>")

    users_col.update_one(
        {"user_id": target.id}, 
        {"$set": {"coins": 0, "vault": 0, "rank_score": 1000, "deducted_50": 0}}
    )
    
    await message.reply(
        f"<b>┏━━「 🔄 ʀᴇsᴇᴛ sᴜᴄᴄᴇss 」━━┓</b>\n"
        f"<b>┃ 👤 ᴀᴅᴍɪɴ: {m_admin}</b>\n"
        f"<b>┃ 👤 ᴜsᴇʀ: {get_mention(target.id, target.first_name)}</b>\n"
        f"<b>┃ ⚠️ sᴛᴀᴛᴜs: ᴀᴄᴄᴏᴜɴᴛ ᴡɪᴘᴇᴅ</b>\n"
        f"<b>┗━━━━━━━━━━━━━━━┛</b>"
    )

@app.on_message(filters.command(["cban", "cunban"]))
async def ban_system(client, message):
    if not await check_sudo(message.from_user.id): return await del_cmd(message)
    cmd = message.command[0]
    parts = message.text.split()
    target = await get_target_user(client, message, parts)
    m_admin = get_mention(message.from_user.id, message.from_user.first_name)

    if not target: return await message.reply(f"<b>⚠️ {m_admin}, ᴜsᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ!</b>")
    if target.id in INIT_SUDO or target.id == OWNER_ID:
        return await message.reply(f"<b>❌ {m_admin}, ᴄᴀɴɴᴏᴛ ʙᴀɴ sᴜᴅᴏ!</b>")

    sync_data(target)
    
    if cmd == "cban":
        users_col.update_one({"user_id": target.id}, {"$set": {"is_banned": 1}})
        await message.reply(
            f"<b>┏━━「 ⛔ ʙᴀɴɴᴇᴅ 」━━┓</b>\n"
            f"<b>┃ 👤 ᴀᴅᴍɪɴ: {m_admin}</b>\n"
            f"<b>┃ 👤 ᴜsᴇʀ: {get_mention(target.id, target.first_name)}</b>\n"
            f"<b>┃ 🔨 sᴛᴀᴛᴜs: ʙʟᴏᴄᴋᴇᴅ</b>\n"
            f"<b>┗━━━━━━━━━━━━━━┛</b>"
        )
    elif cmd == "cunban":
        users_col.update_one({"user_id": target.id}, {"$set": {"is_banned": 0}})
        await message.reply(
            f"<b>┏━━「 🟢 ᴜɴʙᴀɴɴᴇᴅ 」━━┓</b>\n"
            f"<b>┃ 👤 ᴀᴅᴍɪɴ: {m_admin}</b>\n"
            f"<b>┃ 👤 ᴜsᴇʀ: {get_mention(target.id, target.first_name)}</b>\n"
            f"<b>┃ 🕊️ sᴛᴀᴛᴜs: ғʀᴇᴇ</b>\n"
            f"<b>┗━━━━━━━━━━━━━━┛</b>"
        )

# --- USER COMMANDS ---

@app.on_message(filters.command("data") & (filters.group | filters.private))
async def data_handler(client, message):
    if not await check_sudo(message.from_user.id): return await del_cmd(message)

    parts = message.text.split()
    target = await get_target_user(client, message, parts)

    if target or (len(parts) > 1 and not parts[1].isdigit()):
        if not target: return await message.reply("<b>⚠️ ᴜsᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ!</b>")

        u_db = users_col.find_one({"user_id": target.id})
        if u_db:
            badge, stars, r_name = get_rank_info(u_db.get('coins', 0))
            status = "🔴 ʙᴀɴɴᴇᴅ" if u_db.get("is_banned", 0) == 1 else "🟢 ᴜɴʙᴀɴɴᴇᴅ"
            pocket = u_db.get('coins', 0)
            vault = u_db.get('vault', 0)
            date_str = datetime.now().strftime("%d-%m-%Y")
        else:
            badge, stars, r_name = ("⚪️", "🌑", "ɴᴏᴛ ɪɴ ᴅʙ")
            status, pocket, vault, date_str = ("🟢 ᴜɴʙᴀɴɴᴇᴅ", 0, 0, "ɴ/ᴀ")

        caption = (
            f"<b>┏━━「 👤 ᴜsᴇʀ ɪɴғᴏ 」━━┓</b>\n"
            f"<b>┃ 👤 ᴜsᴇʀ: {get_mention(target.id, target.first_name)}</b>\n"
            f"<b>┃ 🆔 ɪᴅ: <code>{target.id}</code></b>\n"
            f"<b>┃ 📛 ɴᴀᴍᴇ: {target.first_name} {target.last_name or ''}</b>\n"
            f"<b>┃ 📧 ᴜsᴇʀ: @{target.username or 'ɴᴏɴᴇ'}</b>\n"
            f"<b>┣━━━━━━━━━━━━━━</b>\n"
            f"<b>┃ ᴘᴏᴄᴋᴇᴛ: {pocket}</b>\n"
            f"<b>┃ ᴠᴀᴜʟᴛ: {vault}</b>\n"
            f"<b>┃ ʙᴀᴅɢᴇ: {badge} ({r_name})</b>\n"
            f"<b>┃ sᴛᴀʀs: {stars}</b>\n"
            f"<b>┃ sᴛᴀᴛᴜs: {status}</b>\n"
            f"<b>┃ ᴅᴀᴛᴇ: {date_str}</b>\n"
            f"<b>┗━━━━━━━━━━━━━━┛</b>"
        )
        try:
            photos = [p async for p in client.get_chat_photos(target.id, limit=1)]
            if photos: await message.reply_photo(photos[0].file_id, caption=caption)
            else: await message.reply(caption)
        except: await message.reply(caption)
        return

    await del_cmd(message)
    status_msg = await message.reply("<b>⏳ ɢᴇɴᴇʀᴀᴛɪɴɢ ᴅᴀᴛᴀ ғɪʟᴇ...</b>")
    
    all_users = list(users_col.find())
    total_users = len(all_users)
    banned_users = users_col.count_documents({"is_banned": 1})
    
    output = f"TOTAL USERS: {total_users}\nBANNED USERS: {banned_users}\n" + "="*30 + "\n\n"
    
    for u in all_users:
        u_id = u.get("user_id")
        name = u.get("full_name", "Unknown")
        uname = u.get("username", "None")
        coins = u.get("coins", 0)
        vault = u.get("vault", 0)
        is_ban = "Banned" if u.get("is_banned", 0) == 1 else "Unban"
        badge, stars, _ = get_rank_info(coins)
        
        output += (
            f"ᴜɪᴅ: {u_id}\nɴᴀᴍᴇ: {name}\nᴜsᴇʀ: @{uname}\n"
            f"ᴘᴏᴄᴋᴇᴛ: {coins}\nᴠᴀᴜʟᴛ: {vault}\nʙᴀᴅɢᴇ: {badge}\n"
            f"sᴛᴀʀs: {stars}\nsᴛᴀᴛᴜs: {is_ban}\n"
            f"ᴅᴀᴛᴇ: {datetime.now().strftime('%Y-%m-%d')}\n{'-'*20}\n"
        )

    f = io.BytesIO(output.encode())
    f.name = f"DX_Users_Data_{datetime.now().strftime('%d_%m')}.txt"
    caption = (f"<b>┏━━「 📂 ᴅᴀᴛᴀʙᴀsᴇ ᴇxᴘᴏʀᴛ 」━━┓</b>\n"
               f"<b>┃ 📊 ᴛᴏᴛᴀʟ: {total_users}</b>\n"
               f"<b>┃ 🚫 ʙᴀɴɴᴇᴅ: {banned_users}</b>\n"
               f"<b>┃ 🛡️ ᴀᴅᴍɪɴ: {get_mention(message.from_user.id, message.from_user.first_name)}</b>\n"
               f"<b>┗━━━━━━━━━━━━━━┛</b>")
    await client.send_document(message.chat.id, f, caption=caption)
    await status_msg.delete()

@app.on_message(filters.command("claim") & filters.group)
async def daily_claim(client, message):
    m = get_mention(message.from_user.id, message.from_user.first_name)
    user = users_col.find_one({"user_id": message.from_user.id})
    
    if not is_dark_user(message.from_user):
        await del_cmd(message)
        return await message.reply(
            f"<b>┏━━「 ⚠️ ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ 」━━┓</b>\n"
            f"<b>┃ 👤 ᴜsᴇʀ: {m}</b>\n"
            f"<b>┃ ❌ ᴇʀʀᴏʀ: ɴᴏᴛ ᴀ ᴅᴀʀᴋ ᴜsᴇʀ</b>\n"
            f"<b>┃ 💡 ɪɴғᴏ: ғᴏʀ 'ᴅᴀʀᴋ' ʙʀᴏᴛʜᴇʀs ᴏɴʟʏ</b>\n"
            f"<b>┗━━━━━━━━━━━━━━━━┛</b>"
        )

    now = time.time()
    if now - user.get("last_claim", 0) < 259200:
        await del_cmd(message)
        rem = 259200 - (now - user.get("last_claim", 0))
        return await message.reply(
            f"<b>┏━━「 ⏳ ᴄᴏᴏʟᴅᴏᴡɴ 」━━┓</b>\n"
            f"<b>┃ 👤 ᴜsᴇʀ: {m}</b>\n"
            f"<b>┃ 🕒 ᴡᴀɪᴛ: {str(timedelta(seconds=int(rem)))}</b>\n"
            f"<b>┗━━━━━━━━━━━━━━┛</b>"
        )

    await del_cmd(message)
    users_col.update_one({"user_id": message.from_user.id}, {"$set": {"last_claim": now}})
    await handle_coin_update(client, message.chat.id, message.from_user, 1)
    
    await message.reply(
        f"<b>┏━━「 ✅ ᴄʟᴀɪᴍᴇᴅ 」━━┓</b>\n"
        f"<b>┃ 👤 ᴜsᴇʀ: {m}</b>\n"
        f"<b>┃ 💰 ʀᴇᴡᴀʀᴅ: +1 ᴄᴏɪɴ</b>\n"
        f"<b>┗━━━━━━━━━━━━━━┛</b>"
    )

@app.on_message(filters.command("menu") & filters.group)
async def menu_handler(client, message):
    await del_cmd(message)
    m = get_mention(message.from_user.id, message.from_user.first_name)
    await message.reply_text(
        f"<b>┏━━「 ✨ {B} ᴍᴇɴᴜ 」━━┓</b>\n"
        f"<b>┃ 👤 ʜɪ: {m}</b>\n"
        f"<b>┣━━━━━━━━━━</b>\n"
        f"<b>┃ 📊 /coin  • ᴄʜᴇᴄᴋ ᴄᴏɪɴ</b>\n"
        f"<b>┃ 🏆 /ctop  • ʟᴇᴀᴅᴇʀʙᴏᴀʀᴅ</b>\n"
        f"<b>┃ 🌟 /star  • sᴛᴀʀ ʟɪsᴛ</b>\n"
        f"<b>┃ 🎁 /claim • ᴅᴀɪʟʏ ᴄᴏɪɴ</b>\n"
        f"<b>┃ 💸 /gift  • sᴇɴᴅ ᴄᴏɪɴ</b>\n"
        f"<b>┃ 🏦 /vault • sᴀᴠᴇ ᴄᴏɪɴ</b>\n"
        f"<b>┃ 📜 /crules• ʙᴏᴛ ʀᴜʟᴇs</b>\n"
        f"<b>┃ ⚡ /sudo  • ᴀᴅᴍɪɴ ʟɪsᴛ</b>\n"
        f"<b>┃ 🛠️ /cusage• sᴜᴅᴏ ʜᴇʟᴘ</b>\n"
        f"<b>┗━━━━━━━━━━┛</b>"
    )

@app.on_message(filters.command(["coin", "mycoin"]) & filters.group)
async def check_stats(client, message):
    await del_cmd(message)
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    sync_data(target)
    user = users_col.find_one({"user_id": target.id})
    badge, stars, rank_n = get_rank_info(user['coins'])
    
    # Calculate Leaderboard position by sorting 'rank_score' Ascending
    user_rank_score = user.get('rank_score', 1000)
    g_rank = users_col.count_documents({"rank_score": {"$lt": user_rank_score}}) + 1
    
    m = get_mention(target.id, target.first_name)
    star_status = "✨ ᴠᴇʀɪғɪᴇᴅ" if user.get("deducted_50") == 1 else "❌ ɴᴏᴛ ʏᴇᴛ"
    
    await message.reply_text(
        f"<b>┏━━「 📊 ᴘʀᴏғɪʟᴇ 」━━┓</b>\n"
        f"<b>┃ 👤 ɴᴀᴍᴇ: {m}</b>\n"
        f"<b>┃ 🆔 ᴜɪᴅ: <code>{target.id}</code></b>\n"
        f"<b>┣━━━━━━━━━━</b>\n"
        f"<b>┃ 💰 ᴘᴏᴄᴋᴇᴛ: {user['coins']}</b>\n"
        f"<b>┃ 🏦 ᴠᴀᴜʟᴛ: {user.get('vault', 0)}</b>\n"
        f"<b>┃ 🏆 ʀᴀɴᴋ: #{g_rank} </b> (P: {user_rank_score})\n"
        f"<b>┃ 🎖️ ʙᴀᴅɢᴇ: {badge} ({rank_n})</b>\n"
        f"<b>┃ ⭐ sᴛᴀʀs: {stars}</b>\n"
        f"<b>┃ 🧿 sᴛᴀᴛᴜs: {star_status}</b>\n"
        f"<b>┗━━━━━━━━━━┛</b>"
    )

@app.on_message(filters.command("ctop") & filters.group)
async def leaderboard(client, message):
    await del_cmd(message)
    # Changed algorithm: sorted by lowest rank_score first, then highest coins
    rows = list(users_col.find().sort([("rank_score", 1), ("coins", -1)]).limit(10))
    board = f"<b>┏━━「 🏆 ᴛᴏᴘ ʀɪᴄʜᴇsᴛ 」━━┓</b>\n"
    for i, row in enumerate(rows, 1):
        icon = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"<b>{i}.</b>"
        badge, _, _ = get_rank_info(row.get('coins',0))
        u_name = row.get('full_name', 'User')[:12]
        board += f"<b>┃ {icon} {get_mention(row['user_id'], u_name)}</b>\n"
        board += f"<b>┃ ╰╼ ID: <code>{row['user_id']}</code> • 💰 {row.get('coins',0)} {badge}</b>\n"
    board += f"<b>┗━━━━━━━━━━┛</b>"
    await message.reply_text(board)

@app.on_message(filters.command("star") & filters.group)
async def star_list(client, message):
    await del_cmd(message)
    stars = users_col.find({
        "$or": [{"coins": {"$gte": 50}}, {"deducted_50": 1}]
    }).sort([("rank_score", 1), ("coins", -1)]).limit(15)
    
    text = f"<b>┏━━「 🌟 sᴛᴀʀ ʜᴏʟᴅᴇʀs 」━━┓</b>\n"
    count = 0
    for u in stars:
        count += 1
        badge, s_icon, r_name = get_rank_info(u.get('coins', 0))
        is_deducted = "🔹" if u.get("deducted_50") == 1 else ""
        text += f"<b>┃ {count}. {get_mention(u['user_id'], u.get('full_name'))} {is_deducted}</b>\n"
        text += f"<b>┃ ╰╼ {badge} • {u['coins']} ({s_icon})</b>\n"
    if count == 0: text += "<b>┃ ❌ ɴᴏ sᴛᴀʀ ʜᴏʟᴅᴇʀs ʏᴇᴛ!</b>\n"
    text += f"<b>┗━━━━━━━━━━┛</b>"
    await message.reply(text)

@app.on_message(filters.command("gift") & filters.group)
async def gift_coin(client, message):
    m = get_mention(message.from_user.id, message.from_user.first_name)
    parts = message.text.split()
    if len(parts) < 2: return await message.reply(f"<b>⚠️ {m}, ᴀᴍᴏᴜɴᴛ?</b>")
    try: amt = int(parts[1])
    except: return
    
    await del_cmd(message)
    
    # Check for negative logic 
    if amt <= 0: return await message.reply(f"<b>❌ {m}, ɪɴᴠᴀʟɪᴅ ᴀᴍᴏᴜɴᴛ!</b>")
        
    target = await get_target_user(client, message, parts)
    
    if not target or target.id == message.from_user.id: 
        return await message.reply(f"<b>❌ {m}, ɪɴᴠᴀʟɪᴅ ᴜsᴇʀ!</b>")
    
    sender = users_col.find_one({"user_id": message.from_user.id})
    if sender and sender['coins'] >= amt:
        users_col.update_one({"user_id": message.from_user.id}, {"$inc": {"coins": -amt}})
        await handle_coin_update(client, message.chat.id, target, amt)
        await message.reply(f"<b>┏━━「 💸 sᴇɴᴛ 」━━┓\n┃ 👤 ғʀᴏᴍ: {m}\n┃ 👤 ᴛᴏ: {get_mention(target.id, target.first_name)}\n┃ 💰 ᴀᴍᴛ: {amt}\n┗━━━━━━━━━━┛</b>")
    else: await message.reply(f"<b>❌ {m}, ɴᴏᴛ ᴇɴᴏᴜɢʜ!</b>")

@app.on_message(filters.command("vault") & filters.group)
async def vault_handler(client, message):
    await del_cmd(message)
    m = get_mention(message.from_user.id, message.from_user.first_name)
    
    # --- Passive Vault Income Engine (Every 7 days adds 1 coin) ---
    sync_data(message.from_user) 
    user = users_col.find_one({"user_id": message.from_user.id})
    
    last_calc = user.get('vault_last_calc', time.time())
    now = time.time()
    elapsed_days = (now - last_calc) / (24 * 3600)
    
    if elapsed_days >= 7:
        weeks_passed = int(elapsed_days // 7)
        added_coins = weeks_passed * 1
        new_vault = user.get('vault', 0) + added_coins
        new_calc = last_calc + (weeks_passed * 7 * 24 * 3600)
        
        users_col.update_one(
            {"user_id": message.from_user.id}, 
            {"$set": {"vault": new_vault, "vault_last_calc": new_calc}}
        )
        user['vault'] = new_vault # Update var for UI 
    # -------------------------------------------------------------

    parts = message.text.split()
    if len(parts) == 1:
        return await message.reply(f"<b>┏━━「 🏦 ᴠᴀᴜʟᴛ 」━━┓\n┃ 👤 ᴜsᴇʀ: {m}\n┃ 💰 sᴀᴠᴇᴅ: {user.get('vault', 0)}\n┗━━━━━━━━━━┛</b>")
    try:
        act, amt = parts[1].lower(), int(parts[2])
        if amt <= 0: return await message.reply(f"<b>❌ {m}, ɪɴᴠᴀʟɪᴅ!</b>") # Anti-negative
        
        if act in ["dep", "d"] and user['coins'] >= amt:
            users_col.update_one({"user_id": message.from_user.id}, {"$inc": {"coins": -amt, "vault": amt}})
            await message.reply(f"<b>✅ {m}, sᴀᴠᴇᴅ {amt}!</b>")
        elif act in ["wd", "w"] and user.get('vault', 0) >= amt:
            users_col.update_one({"user_id": message.from_user.id}, {"$inc": {"coins": amt, "vault": -amt}})
            await message.reply(f"<b>✅ {m}, ᴡɪᴛʜᴅʀᴇᴡ {amt}!</b>")
    except: pass

@app.on_message(filters.command("crules") & filters.group)
async def rules_h(client, message):
    await del_cmd(message)
    m = get_mention(message.from_user.id, message.from_user.first_name)
    await message.reply_text(
        f"<b>┏━━━「 📜 {B} ʀᴜʟᴇs 」━━━┓</b>\n"
        f"<b>┃ 👤: {m}</b>\n"
        f"<b>┣━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>┃ 🔸 ᴅᴀʀᴋ ɢᴀɴɢ ᴜ-ᴀᴅᴅ: 2 ᴄᴏɪɴ</b>\n"
        f"<b>┃ 🔹 ᴀᴅᴅᴀ ɢ-ʜᴀᴄᴋ(500+): 5 ᴄᴏɪɴ</b>\n"
        f"<b>┃ 🔹 ᴀᴅᴅᴀ ɢ-ʜᴀᴄᴋ(-500): 3 ᴄᴏɪɴ</b>\n"
        f"<b>┃ 🔸 ʜᴏᴛʟɪɴᴇ ɢ-ʜᴀᴄᴋ: 10 ᴄᴏɪɴ</b>\n"
        f"<b>┃ 🔹 -15 ʏ-ɢʀᴏᴜᴘ ʜᴀᴄᴋ: 12 ᴄᴏɪɴ</b>\n"
        f"<b>┣━━━━━ 🎖️ sᴛᴀʀs ━━━━━</b>\n"
        f"<b>┃ ⭐: 50+ (ᴅᴇs-ɴᴀᴍᴇ)</b>\n"
        f"<b>┃ ⭐⭐: 100+ (ʜ-ᴄᴀᴘᴛᴀɪɴ)</b>\n"
        f"<b>┃ ⭐⭐⭐: 200+ (ʀᴜʟᴇʀ)</b>\n"
        f"<b>┃ 💎: 400+ (ᴄᴏᴅᴇ ᴏᴡɴᴇʀ)</b>\n"
        f"<b>┗━━━━━━━━━━━━━━━━┛</b>"
    )

@app.on_message(filters.command("cusage") & filters.group)
async def sudo_usage(client, message):
    if not await check_sudo(message.from_user.id): return await del_cmd(message)
    await del_cmd(message)
    m = get_mention(message.from_user.id, message.from_user.first_name)
    await message.reply(
        f"<b>┏━━「 🛠️ sᴜᴅᴏ ʜᴇʟᴘ 」━━┓</b>\n"
        f"<b>┃ 👤 ᴀᴅᴍɪɴ: {m}</b>\n"
        f"<b>┣━━━━━━━━━━━━━━</b>\n"
        f"<b>┃ ➕ /acoin (ɪᴅ/@/ʀᴇᴘ) (ᴀᴍᴛ)</b>\n"
        f"<b>┃ ➖ /mcoin (ɪᴅ/@/ʀᴇᴘ) (ᴀᴍᴛ)</b>\n"
        f"<b>┃ 🔄 /reset (ɪᴅ/@/ʀᴇᴘ) - ᴡɪᴘᴇ ᴀᴄᴄ</b>\n"
        f"<b>┃ ⛔ /cban (ɪᴅ/@/ʀᴇᴘ)</b>\n"
        f"<b>┃ 🟢 /cunban (ɪᴅ/@/ʀᴇᴘ)</b>\n"
        f"<b>┃ ⚡ /sudo (ʀᴇᴘʟʏ) - ᴀᴅᴅ</b>\n"
        f"<b>┗━━━━━━━━━━━━━━┛</b>"
    )

@app.on_message(filters.command("sudo") & filters.group)
async def sudo_h(client, message):
    if not await check_sudo(message.from_user.id): return await del_cmd(message)
    await del_cmd(message)
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        users_col.update_one({"user_id": target.id}, {"$set": {"is_sudo": 1}})
        await message.reply(f"<b>┏━━「 🟢 sᴜᴅᴏ 」━━┓\n┃ 👤 ᴀᴅᴅᴇᴅ: {get_mention(target.id, target.first_name)}\n┗━━━━━━━━━━┛</b>")
    else:
        sudos = list(users_col.find({"is_sudo": 1}))
        res = f"<b>┏━━「 ✨ sᴜᴅᴏs 」━━┓\n"
        for i, s in enumerate(sudos, 1): res += f"┃ {i}. {get_mention(s['user_id'], s.get('full_name'))}\n"
        res += "┗━━━━━━━━━━┛</b>"
        await message.reply(res)

@app.on_message(filters.group & ~filters.bot)
async def auto_sync(client, message):
    if message.from_user: sync_data(message.from_user)

async def start_bot():
    print(f"{B} SYSTEM STARTING...")
    await app.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    Thread(target=run_web).start()
    Thread(target=keep_alive_ping, daemon=True).start()
    asyncio.get_event_loop().run_until_complete(start_bot())

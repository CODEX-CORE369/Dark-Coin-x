import asyncio
import os
import re
import time
import requests
import unicodedata
import re
from datetime import timedelta
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
# The username of the allowed group (without @)
ALLOWED_GROUP_USERNAME = "Dark_Zone_x" 

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
    # এখানে তোমার Render এর URL টা বসাবে
    URL = "https://dark-coin-x.onrender.com" 
    while True:
        try:
            requests.get(URL)
            print(f"[{B}] Pinging server to stay awake...")
        except Exception as e:
            print(f"[{B}] Ping failed: {e}")
        time.sleep(300) # ৩০০ সেকেন্ড মানে ৫ মিনিট

async def check_sudo(user_id):
    if user_id in INIT_SUDO or user_id == OWNER_ID: return True
    user = users_col.find_one({"user_id": user_id})
    return user.get("is_sudo", 0) == 1 if user else False

def get_mention(user_id, name):
    name = re.sub(r'[<>#]', '', str(name)) if name else "Usᴇʀ"
    return f"<a href='tg://user?id={user_id}'>{name[:15]}</a>"

def get_rank_info(coins):
    # Ranks based on total value (logic adapted so deducted users still keep rank if designed)
    if coins >= 400: return ("💎", "💎💎💎", "ᴄᴏᴅᴇ ᴏᴡɴᴇʀ")
    elif coins >= 200: return ("🌟🌟🌟", "⭐⭐⭐", "ᴀᴅ/ʀᴜʟᴇʀ")
    elif coins >= 100: return ("🌟🌟", "⭐⭐", "ʜ-ᴄᴀᴘᴛᴀɪɴ")
    elif coins >= 50: return ("🌟", "⭐", "ᴅᴇs-ɴᴀᴍᴇ")
    return ("⚪️", "🌑", "ᴍᴇᴍʙᴇʀ")

def sync_data(user):
    if not user: return
    users_col.update_one(
        {"user_id": user.id},
        {"$set": {"full_name": f"{user.first_name} {user.last_name or ''}".strip(), "username": user.username},
         "$setOnInsert": {
             "coins": 0, 
             "vault": 0, 
             "last_claim": 0, 
             "is_sudo": 0,
             "deducted_50": 0, # Track if 50 coins were deducted
             "is_banned": 0
         }},
        upsert=True
    )

async def del_cmd(message):
    try: await message.delete()
    except: pass

async def get_target_user(client, message, parts):
    # Priority 1: Reply
    if message.reply_to_message: 
        return message.reply_to_message.from_user
    # Priority 2: Mention or ID in args
    if len(parts) > 1:
        u_input = parts[1] # Check the second word
        # If it's a number (ID)
        if u_input.isdigit(): 
            try: return await client.get_users(int(u_input))
            except: pass
        # If it's a username (@user)
        if u_input.startswith("@"):
            try: return await client.get_users(u_input)
            except: pass
        # Sometimes user puts command amount user, handle flexibility
        if len(parts) > 2:
            u_input_2 = parts[2]
            if u_input_2.isdigit() or u_input_2.startswith("@"):
                try: return await client.get_users(u_input_2)
                except: pass
    return None

def advanced_cleaner(text):
    """সর্বোচ্চ পর্যায়ের ক্লিনিং অ্যালগরিদম: স্টাইলিশ ফন্ট, গ্লিচ, লেটার রিপ্লেসমেন্ট এবং সিম্বল হ্যান্ডেল করে।"""
    if not text:
        return ""
    
    # ১. ইউনিকোড নরমালিস্টেশন (স্টাইলিশ ফন্ট যেমন ᴅᴀʀᴋ, 𝖉𝖆𝖗𝖐 ঠিক করা)
    text = unicodedata.normalize('NFKC', text).lower()
    
    # ২. লেটার রিপ্লেসমেন্ট ম্যাপ (Leet Speak এবং সিম্বল ডিটেকশন)
    # মানুষ 'dark' লিখতে যে ধরণের ট্রিকস ব্যবহার করে সেগুলোকে সাধারণ লেটারে কনভার্ট করা
    mapping = {
        '0': 'o', '4': 'a', '@': 'a', '8': 'b', '3': 'e', '1': 'i', '!': 'i', 
        '$': 's', '7': 't', '(': 'c', '[': 'c', '{': 'c', '©': 'c', 
        '|)': 'd', '|>': 'd', 'cl': 'd', 'v': 'v', '×': 'x'
    }
    for char, replacement in mapping.items():
        text = text.replace(char, replacement)
        
    # ৩. ডায়াক্রিটিক্যাল মার্কস বা গ্লিচ (Zalgo Text) রিমুভ করা
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    
    # ৪. রেজেক্স ক্লিনিং: শুধুমাত্র a থেকে z পর্যন্ত লেটারগুলো রাখা (বাকি সব ডিলিট)
    # এটি d.a.r.k, d-a-r-k, d a r k সবগুলোকে 'dark' বানিয়ে ফেলবে
    clean_text = re.sub(r'[^a-z]', '', text)
    
    return clean_text

def is_dark_user(user):
    """সবচেয়ে অ্যাডভান্সড চেকিং: যেকোনো অবস্থায় 'dark' থাকলে ট্রু রিটার্ন করবে।"""
    # ইউজারের ডাটাবেস বা মেসেজ থেকে প্রাপ্ত নাম ও ইউজারনেম এক করা
    data_to_scan = f"{user.first_name or ''} {user.last_name or ''} {user.username or ''}"
    
    # ক্লিনিং অ্যালগরিদম চালানো
    processed_text = advanced_cleaner(data_to_scan)
    
    # চেক করা (এমনকি d.4.r.k বা |)ark থাকলেও এটি এখন কাজ করবে)
    return "dark" in processed_text
# --- MILESTONE LOGIC ---
async def handle_coin_update(client, chat_id, user, amt_added):
    """
    Handles coin addition, 50 coin deduction, and congratulations.
    """
    user_id = user.id
    user_db = users_col.find_one({"user_id": user_id})
    if not user_db: return

    old_coins = user_db.get("coins", 0)
    deducted_flag = user_db.get("deducted_50", 0)
    
    # Tentative new balance
    new_coins_temp = old_coins + amt_added
    
    # 1. Check for 50 Coin Milestone (First Time Only)
    if deducted_flag == 0 and new_coins_temp >= 50:
        # User reached 50 for first time. 
        # Logic: Deduct 50, set flag = 1.
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
        return # Exit to avoid double congrats
        
    else:
        # Regular update
        users_col.update_one({"user_id": user_id}, {"$set": {"coins": new_coins_temp}})
        final_coins = new_coins_temp

    # 2. Check for other Rank Ups (100, 200, 400)
    # We compare badges
    old_badge, _, _ = get_rank_info(old_coins)
    new_badge, stars, r_name = get_rank_info(final_coins)

    if new_badge != old_badge and final_coins > old_coins:
        # Only congrats if they went UP a tier (not down) and it's a major tier
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
    """Ensures bot leaves unauthorized groups."""
    if message.chat.username != ALLOWED_GROUP_USERNAME:
        try:
            await message.reply(
                f"<b>┏━━「 🚫 ʟᴇᴀᴠɪɴɢ 」━━┓</b>\n"
                f"<b>┃ ⚠️ ᴀʟᴇʀᴛ: ᴡʀᴏɴɢ ᴢᴏɴᴇ</b>\n"
                f"<b>┃ 🛡️ ᴏɴʟʏ ғᴏʀ: @{ALLOWED_GROUP_USERNAME}</b>\n"
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
    
    cmd = message.command[0] # acoin or mcoin
    parts = message.text.split()
    target = await get_target_user(client, message, parts)
    
    # Try to find amount in parts
    amount = 0
    for p in parts:
        if p.isdigit():
            amount = int(p)
            break
            
    m_admin = get_mention(message.from_user.id, message.from_user.first_name)
    
    if not target: 
        return await message.reply(f"<b>⚠️ {m_admin}, ᴜsᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ!</b>")
    if amount == 0:
        return await message.reply(f"<b>⚠️ {m_admin}, ᴇɴᴛᴇʀ ᴀᴍᴏᴜɴᴛ!</b>")

    sync_data(target)
    
    if cmd == "acoin":
        await handle_coin_update(client, message.chat.id, target, amount)
        # Fetch updated data for display
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

@app.on_message(filters.command(["cban", "cunban"]))
async def ban_system(client, message):
    if not await check_sudo(message.from_user.id): 
        return await del_cmd(message)
    
    cmd = message.command[0]
    parts = message.text.split()
    target = await get_target_user(client, message, parts)
    m_admin = get_mention(message.from_user.id, message.from_user.first_name)

    if not target: 
        return await message.reply(f"<b>⚠️ {m_admin}, ᴜsᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ!</b>")
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

@app.on_message(filters.command("claim") & filters.group)
async def daily_claim(client, message):
    # Only this command doesn't delete immediately if successful, but logic says delete and reply
    m = get_mention(message.from_user.id, message.from_user.first_name)
    user = users_col.find_one({"user_id": message.from_user.id})
    
    # 1. Check Name
    if not is_dark_user(message.from_user):
        await del_cmd(message) # Delete user message
        await message.reply(
            f"<b>┏━━「 ⚠️ ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ 」━━┓</b>\n"
            f"<b>┃ 👤 ᴜsᴇʀ: {m}</b>\n"
            f"<b>┃ ❌ ᴇʀʀᴏʀ: ɴᴏᴛ ᴀ ᴅᴀʀᴋ ᴜsᴇʀ</b>\n"
            f"<b>┃ 💡 ɪɴғᴏ: ғᴏʀ 'ᴅᴀʀᴋ' ʙʀᴏᴛʜᴇʀs ᴏɴʟʏ</b>\n"
            f"<b>┗━━━━━━━━━━━━━━━━━┛</b>"
        )
        return

    # 2. Check Time
    now = time.time()
    if now - user.get("last_claim", 0) < 259200:
        await del_cmd(message)
        rem = 259200 - (now - user.get("last_claim", 0))
        await message.reply(
            f"<b>┏━━「 ⏳ ᴄᴏᴏʟᴅᴏᴡɴ 」━━┓</b>\n"
            f"<b>┃ 👤 ᴜsᴇʀ: {m}</b>\n"
            f"<b>┃ 🕒 ᴡᴀɪᴛ: {str(timedelta(seconds=int(rem)))}</b>\n"
            f"<b>┗━━━━━━━━━━━━━━┛</b>"
        )
        return

    # 3. Add Coin (uses helper for 50 deduction logic)
    await del_cmd(message)
    users_col.update_one({"user_id": message.from_user.id}, {"$set": {"last_claim": now}})
    await handle_coin_update(client, message.chat.id, message.from_user, 1)
    
    # Reply success
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
    
    # Rank calc
    g_rank = users_col.count_documents({"coins": {"$gt": user['coins']}}) + 1
    m = get_mention(target.id, target.first_name)
    
    # Check if they are a 'Star' (deducted status or high coins)
    star_status = "✨ ᴠᴇʀɪғɪᴇᴅ" if user.get("deducted_50") == 1 else "❌ ɴᴏᴛ ʏᴇᴛ"
    
    await message.reply_text(
        f"<b>┏━━「 📊 ᴘʀᴏғɪʟᴇ 」━━┓</b>\n"
        f"<b>┃ 👤 ɴᴀᴍᴇ: {m}</b>\n"
        f"<b>┃ 🆔 ᴜɪᴅ: <code>{target.id}</code></b>\n"
        f"<b>┣━━━━━━━━━━</b>\n"
        f"<b>┃ 💰 ᴘᴏᴄᴋᴇᴛ: {user['coins']}</b>\n"
        f"<b>┃ 🏦 ᴠᴀᴜʟᴛ: {user.get('vault', 0)}</b>\n"
        f"<b>┃ 🏆 ʀᴀɴᴋ: #{g_rank}</b>\n"
        f"<b>┃ 🎖️ ʙᴀᴅɢᴇ: {badge} ({rank_n})</b>\n"
        f"<b>┃ ⭐ sᴛᴀʀs: {stars}</b>\n"
        f"<b>┃ 🧿 sᴛᴀᴛᴜs: {star_status}</b>\n"
        f"<b>┗━━━━━━━━━━┛</b>"
    )

@app.on_message(filters.command("ctop") & filters.group)
async def leaderboard(client, message):
    await del_cmd(message)
    rows = list(users_col.find().sort("coins", -1).limit(10))
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
    # Stars are people who have coins >= 50 OR have had 50 deducted
    stars = users_col.find({
        "$or": [{"coins": {"$gte": 50}}, {"deducted_50": 1}]
    }).sort("coins", -1).limit(15)
    
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
    target = await get_target_user(client, message, parts)
    
    await del_cmd(message) # Delete command
    
    if not target or target.id == message.from_user.id: 
        return await message.reply(f"<b>❌ {m}, ɪɴᴠᴀʟɪᴅ ᴜsᴇʀ!</b>")
    
    sender = users_col.find_one({"user_id": message.from_user.id})
    if sender and sender['coins'] >= amt:
        # Deduct from sender
        users_col.update_one({"user_id": message.from_user.id}, {"$inc": {"coins": -amt}})
        # Add to receiver (using helper to check for 50 coin logic)
        await handle_coin_update(client, message.chat.id, target, amt)
        
        await message.reply(f"<b>┏━━「 💸 sᴇɴᴛ 」━━┓\n┃ 👤 ғʀᴏᴍ: {m}\n┃ 👤 ᴛᴏ: {get_mention(target.id, target.first_name)}\n┃ 💰 ᴀᴍᴛ: {amt}\n┗━━━━━━━━━━┛</b>")
    else: await message.reply(f"<b>❌ {m}, ɴᴏᴛ ᴇɴᴏᴜɢʜ!</b>")

@app.on_message(filters.command("vault") & filters.group)
async def vault_handler(client, message):
    await del_cmd(message)
    m = get_mention(message.from_user.id, message.from_user.first_name)
    user = users_col.find_one({"user_id": message.from_user.id})
    parts = message.text.split()
    if len(parts) == 1:
        return await message.reply(f"<b>┏━━「 🏦 ᴠᴀᴜʟᴛ 」━━┓\n┃ 👤 ᴜsᴇʀ: {m}\n┃ 💰 sᴀᴠᴇᴅ: {user.get('vault', 0)}\n┗━━━━━━━━━━┛</b>")
    try:
        act, amt = parts[1].lower(), int(parts[2])
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
    # Web server thread
    Thread(target=run_web).start()
    
    # Self-ping thread (Stay Awake System)
    Thread(target=keep_alive_ping, daemon=True).start()
    
    # Bot start
    asyncio.get_event_loop().run_until_complete(start_bot())

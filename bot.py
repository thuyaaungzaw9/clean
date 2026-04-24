import os
import json
import re
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

USER_FILE = "users.json"

def load_users():
    if not os.path.exists(USER_FILE):
        return [ADMIN_ID] if ADMIN_ID else []
    with open(USER_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f)

def is_user(user_id):
    return user_id in load_users()

def add_user(user_id):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        save_users(users)

def remove_user(user_id):
    users = load_users()
    if user_id in users and user_id != ADMIN_ID:
        users.remove(user_id)
        save_users(users)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user(user_id):
        await update.message.reply_text("⛔ သင့်အတွက် ခွင့်မပြုပါ။")
        return
    keyboard = [
        [InlineKeyboardButton("📂 /combo (10MB split)", callback_data="help_combo")],
        [InlineKeyboardButton("🧹 /cardclean (extract cards)", callback_data="help_cardclean")],
        [InlineKeyboardButton("✂️ /cn (custom split cards)", callback_data="help_cn")],
        [InlineKeyboardButton("🧽 /cleancombo (remove ads from combo)", callback_data="help_cleancombo")],
        [InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")] if user_id == ADMIN_ID else []
    ]
    reply_markup = InlineKeyboardMarkup([k for k in keyboard if k])
    await update.message.reply_text("🤖 Developer By ThuYa\n/help ကိုနှိပ်၍ command များ ကြည့်ပါ။", reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user(user_id):
        await update.message.reply_text("⛔ No permission")
        return
    text = """
📌 Commands:
/combo [filename] – 10MB split (reply to file also works)
/cardclean – extract credit cards from dump
/cn [number] – split cards file by custom number
/cleancombo – remove ads/spam from email:pass combo files
/admin – admin panel (user add/remove)
"""
    await update.message.reply_text(text)

# combo split (same as before, keep it)
async def combo_split(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user(user_id):
        await update.message.reply_text("⛔ No permission")
        return
    filename = "gmail.txt"
    if context.args:
        filename = context.args[0]
    reply = update.message.reply_to_message
    if reply and reply.document and reply.document.file_name.endswith(".txt"):
        file = await reply.document.get_file()
        filename = f"temp_combo_{user_id}.txt"
        await file.download_to_drive(filename)
        await update.message.reply_text(f"📥 Downloaded: {reply.document.file_name}")
    elif not os.path.exists(filename):
        await update.message.reply_text(f"❌ '{filename}' not found. Reply to a .txt file or use /combo filename.txt")
        return
    chunk_size = 10 * 1024 * 1024
    out_dir = "split_files"
    os.makedirs(out_dir, exist_ok=True)
    file_number = 1
    with open(filename, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            out_path = os.path.join(out_dir, f"part_{file_number}.txt")
            with open(out_path, 'wb') as cf:
                cf.write(chunk)
            file_number += 1
    await update.message.reply_text(f"✅ Split complete → {out_dir}/ (total {file_number-1} files)")
    if filename.startswith("temp_combo"):
        os.remove(filename)

async def cardclean_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user(user_id):
        await update.message.reply_text("⛔ No permission")
        return
    context.user_data["mode"] = "cardclean"
    await update.message.reply_text("📤 Card dump (.txt) ဖိုင်ကို upload လုပ်ပါ (or reply)")

async def cn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user(user_id):
        await update.message.reply_text("⛔ No permission")
        return
    number = 100
    if context.args and context.args[0].isdigit():
        number = int(context.args[0])
    context.user_data["mode"] = "cn_split"
    context.user_data["cn_number"] = number
    await update.message.reply_text(f"✂️ Cards list (.txt) ဖိုင်ကို upload လုပ်ပါ → {number} cards per file")

async def clean_combo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user(user_id):
        await update.message.reply_text("⛔ No permission")
        return
    context.user_data["mode"] = "clean_combo"
    await update.message.reply_text("🧹 Combo file (.txt) ကို upload လုပ်ပါ (or reply)\n\n→ Ads, @usernames, http links တွေ ဖယ်ရှားပြီး **email:pass** သီးသန့်ထုတ်ပေးမယ်")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user(user_id):
        return
    doc = update.message.document
    if not doc.file_name.endswith(".txt"):
        await update.message.reply_text("❌ .txt ဖိုင်သာ လက်ခံပါတယ်။")
        return
    file = await doc.get_file()
    file_path = f"temp_{user_id}.txt"
    await file.download_to_drive(file_path)
    mode = context.user_data.get("mode")
    if mode == "cardclean":
        card_pattern = r'\b(?:\d[ -]*?){13,16}\b'
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        cards = re.findall(card_pattern, content)
        cards = list(set([c.replace(" ", "").replace("-", "") for c in cards if len(c.replace(" ", "").replace("-", "")) >= 13]))
        if not cards:
            await update.message.reply_text("⚠️ ဘာ Card မှ မတွေ့ပါ။")
        else:
            out_file = f"cleaned_{user_id}.txt"
            with open(out_file, 'w') as f:
                f.write("\n".join(cards))
            await update.message.reply_document(document=open(out_file, 'rb'), filename="cleaned_cards.txt")
            os.remove(out_file)
        context.user_data["mode"] = None
    elif mode == "cn_split":
        number = context.user_data.get("cn_number", 100)
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = [line.strip() for line in f if line.strip()]
        if not lines:
            await update.message.reply_text("⚠️ ဖိုင်ထဲမှာ ဘာမှမပါဘူး။")
        else:
            out_dir = "cn_split_cards"
            os.makedirs(out_dir, exist_ok=True)
            total = len(lines)
            part = 1
            for i in range(0, total, number):
                batch = lines[i:i+number]
                out_path = os.path.join(out_dir, f"cards_part_{part}.txt")
                with open(out_path, 'w') as f:
                    f.write("\n".join(batch))
                part += 1
            await update.message.reply_text(f"✅ {total} cards → {part-1} files in {out_dir}/")
        context.user_data["mode"] = None
    elif mode == "clean_combo":
        cleaned = []
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                first_part = line.split()[0] if line.split() else line
                if ':' in first_part and ('@' in first_part or '.com' in first_part or '.net' in first_part):
                    cleaned.append(first_part)
                else:
                    match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}:[^\s]+)', line)
                    if match:
                        cleaned.append(match.group(1))
        cleaned = list(dict.fromkeys(cleaned))
        if not cleaned:
            await update.message.reply_text("⚠️ ဘာ combo မှ မတွေ့ပါ။")
        else:
            out_file = f"clean_combo_{user_id}.txt"
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write("\n".join(cleaned))
            await update.message.reply_document(document=open(out_file, 'rb'), filename="cleaned_combo.txt")
            os.remove(out_file)
        context.user_data["mode"] = None
    else:
        await update.message.reply_text("⚠️ /cardclean , /cn , or /cleancombo command အရင်ခေါ်ပါ။")
    os.remove(file_path)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Admin only")
        return
    keyboard = [
        [InlineKeyboardButton("➕ Add User", callback_data="add_user")],
        [InlineKeyboardButton("➖ Remove User", callback_data="remove_user")],
        [InlineKeyboardButton("📋 List Users", callback_data="list_users")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👑 Admin Panel", reply_markup=reply_markup)

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id != ADMIN_ID:
        await query.edit_message_text("⛔ Unauthorized")
        return
    data = query.data
    if data == "add_user":
        context.user_data["admin_action"] = "add"
        await query.edit_message_text("➕ User ID ကို ရိုက်ထည့်ပြီး /done ပို့ပါ။")
    elif data == "remove_user":
        context.user_data["admin_action"] = "remove"
        await query.edit_message_text("➖ User ID ကို ရိုက်ထည့်ပြီး /done ပို့ပါ။")
    elif data == "list_users":
        users = load_users()
        await query.edit_message_text(f"📋 Users:\n" + "\n".join(map(str, users)))

async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    action = context.user_data.get("admin_action")
    if not action:
        await update.message.reply_text("❌ /admin မှာ add/remove အရင်ရွေးပါ။")
        return
    try:
        target = int(update.message.text.split()[1])
    except:
        await update.message.reply_text("❌ /done <user_id> ပုံစံသုံးပါ။")
        return
    if action == "add":
        add_user(target)
        await update.message.reply_text(f"✅ User {target} added")
    elif action == "remove":
        if target == ADMIN_ID:
            await update.message.reply_text("❌ Admin ကိုမဖျက်ရ")
        else:
            remove_user(target)
            await update.message.reply_text(f"✅ User {target} removed")
    context.user_data["admin_action"] = None

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("combo", combo_split))
    app.add_handler(CommandHandler("cardclean", cardclean_handler))
    app.add_handler(CommandHandler("cn", cn_command))
    app.add_handler(CommandHandler("cleancombo", clean_combo_handler))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(admin_callback))
    app.run_polling()

if __name__ == "__main__":
    main()

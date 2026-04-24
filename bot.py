import os
import json
import re
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

USER_FILE = "users.json"
BRAND = "✨ <b>Developer by ThuYa</b> ✨"
DIVIDER = "━━━━━━━━━━━━━━━━━━"

# ───────────────────────── User store ─────────────────────────
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

# ───────────────────────── UI helpers ─────────────────────────
def main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("📂 Combo Split", callback_data="help_combo"),
            InlineKeyboardButton("🧹 Card Clean", callback_data="help_cardclean"),
        ],
        [
            InlineKeyboardButton("✂️ CN Split", callback_data="help_cn"),
            InlineKeyboardButton("🧽 Clean Combo", callback_data="help_cleancombo"),
        ],
        [InlineKeyboardButton("📖 All Commands", callback_data="help_all")],
    ]
    if user_id == ADMIN_ID:
        rows.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(rows)

def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_menu")]]
    )

def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Add User", callback_data="add_user")],
            [InlineKeyboardButton("➖ Remove User", callback_data="remove_user")],
            [InlineKeyboardButton("📋 List Users", callback_data="list_users")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_menu")],
        ]
    )

WELCOME_TEXT = (
    f"🤖 <b>Welcome to Checkr Bot</b>\n"
    f"{DIVIDER}\n"
    "သင့်အတွက် combo / card cleaning tools များကို\n"
    "လွယ်ကူစွာ အသုံးပြုနိုင်ပါပြီ။\n\n"
    "👇 အောက်က button များကို နှိပ်၍ စတင်ပါ။\n"
    "💡 <i>Tip: File တစ်ခုခုကို <b>Reply</b> ထောက်ပြီး\n"
    "command ရိုက်တာလည်း ရပါတယ်!</i>\n"
    f"{DIVIDER}\n"
    f"{BRAND}"
)

HELP_TEXTS = {
    "help_combo": (
        "📂 <b>/combo</b> — 10MB Split\n"
        f"{DIVIDER}\n"
        "Big <code>.txt</code> ဖိုင်ကို 10MB chunk များခွဲပေးသည်။\n\n"
        "<b>သုံးနည်း ၂ မျိုး:</b>\n"
        "1️⃣ <code>/combo filename.txt</code>\n"
        "2️⃣ ဖိုင်ကို <b>Reply</b> ထောက်ပြီး <code>/combo</code> ရိုက်ပါ ✅"
    ),
    "help_cardclean": (
        "🧹 <b>/cardclean</b> — Card Extractor\n"
        f"{DIVIDER}\n"
        "Dump ထဲက cards များကို ထုတ်ပေးသည်။\n\n"
        "<b>Format:</b> <code>card|mm|yy|cvv</code>\n"
        "<b>သုံးနည်း:</b>\n"
        "• <code>/cardclean</code> ➜ ပြီးရင် .txt upload\n"
        "• <i>သို့မဟုတ်</i> ဖိုင်ကို <b>Reply</b> ထောက်ပြီး\n"
        "  <code>/cardclean</code> ရိုက်ပါ ✅"
    ),
    "help_cn": (
        "✂️ <b>/cn [number]</b> — Custom Split\n"
        f"{DIVIDER}\n"
        "Cards များကို သင်ပြောတဲ့ အရေအတွက်အလိုက် ခွဲပေးသည်။\n\n"
        "<b>ဥပမာ:</b> <code>/cn 100</code>\n"
        "ပြီးရင် <code>.txt</code> ဖိုင် upload (သို့) Reply ✅"
    ),
    "help_cleancombo": (
        "🧽 <b>/cleancombo</b> — Ad Remover\n"
        f"{DIVIDER}\n"
        "Combo ထဲမှ ads, @username, links များဖယ်ပြီး\n"
        "<code>email:pass</code> သီးသန့်ထုတ်ပေးသည်။\n\n"
        "<b>သုံးနည်း:</b>\n"
        "• <code>/cleancombo</code> ➜ .txt upload\n"
        "• <i>သို့မဟုတ်</i> ဖိုင်ကို <b>Reply</b> ထောက်ပြီး\n"
        "  <code>/cleancombo</code> ရိုက်ပါ ✅"
    ),
    "help_all": (
        "📖 <b>All Commands</b>\n"
        f"{DIVIDER}\n"
        "📂 <code>/combo</code> — 10MB split\n"
        "🧹 <code>/cardclean</code> — extract cards\n"
        "✂️ <code>/cn [n]</code> — custom split\n"
        "🧽 <code>/cleancombo</code> — clean ads\n"
        "👑 <code>/admin</code> — admin panel\n\n"
        "💡 <b>Pro Tip:</b>\n"
        "ဘယ် command မဆို <b>file ကို Reply ထောက်</b>ပြီး\n"
        "ရိုက်လို့ရပါတယ် — အရင် upload မလုပ်ဘဲ\n"
        "တိုက်ရိုက် အသုံးပြုနိုင်ပါတယ်! ✅"
    ),
}

# ───────────────────────── Handlers ─────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user(user_id):
        await update.message.reply_text("⛔ သင့်အတွက် ခွင့်မပြုပါ။")
        return
    await update.message.reply_text(
        WELCOME_TEXT,
        reply_markup=main_menu_keyboard(user_id),
        parse_mode=ParseMode.HTML,
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user(user_id):
        await update.message.reply_text("⛔ No permission")
        return
    await update.message.reply_text(
        HELP_TEXTS["help_all"] + f"\n{DIVIDER}\n{BRAND}",
        reply_markup=back_keyboard(),
        parse_mode=ParseMode.HTML,
    )

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data in HELP_TEXTS:
        await query.edit_message_text(
            HELP_TEXTS[data] + f"\n{DIVIDER}\n{BRAND}",
            reply_markup=back_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    elif data == "back_menu":
        await query.edit_message_text(
            WELCOME_TEXT,
            reply_markup=main_menu_keyboard(user_id),
            parse_mode=ParseMode.HTML,
        )
    elif data == "admin_panel":
        if user_id != ADMIN_ID:
            await query.answer("⛔ Admin only", show_alert=True)
            return
        await query.edit_message_text(
            f"👑 <b>Admin Panel</b>\n{DIVIDER}\nUser management tools\n{DIVIDER}\n{BRAND}",
            reply_markup=admin_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    elif data in {"add_user", "remove_user", "list_users"}:
        if user_id != ADMIN_ID:
            await query.answer("⛔ Unauthorized", show_alert=True)
            return
        if data == "add_user":
            context.user_data["admin_action"] = "add"
            await query.edit_message_text(
                "➕ <b>Add User</b>\n"
                f"{DIVIDER}\n"
                "User ID ကို ဤပုံစံဖြင့် ပို့ပါ:\n"
                "<code>/done 123456789</code>",
                reply_markup=back_keyboard(),
                parse_mode=ParseMode.HTML,
            )
        elif data == "remove_user":
            context.user_data["admin_action"] = "remove"
            await query.edit_message_text(
                "➖ <b>Remove User</b>\n"
                f"{DIVIDER}\n"
                "User ID ကို ဤပုံစံဖြင့် ပို့ပါ:\n"
                "<code>/done 123456789</code>",
                reply_markup=back_keyboard(),
                parse_mode=ParseMode.HTML,
            )
        elif data == "list_users":
            users = load_users()
            user_list = "\n".join(f"• <code>{u}</code>" for u in users) or "—"
            await query.edit_message_text(
                f"📋 <b>Registered Users ({len(users)})</b>\n{DIVIDER}\n{user_list}\n{DIVIDER}\n{BRAND}",
                reply_markup=admin_keyboard(),
                parse_mode=ParseMode.HTML,
            )

# ───────────────────────── Combo split ─────────────────────────
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
        await update.message.reply_text(
            f"📥 <b>Downloaded:</b> <code>{reply.document.file_name}</code>",
            parse_mode=ParseMode.HTML,
        )
    elif not os.path.exists(filename):
        await update.message.reply_text(
            f"❌ <code>{filename}</code> မတွေ့ပါ။\n\n"
            "💡 <b>အကြံပြုချက်:</b> ဖိုင်ကို <b>Reply</b> ထောက်ပြီး\n"
            "<code>/combo</code> ရိုက်ပါ။",
            parse_mode=ParseMode.HTML,
        )
        return
    chunk_size = 10 * 1024 * 1024
    out_dir = "split_files"
    os.makedirs(out_dir, exist_ok=True)
    file_number = 1
    with open(filename, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            out_path = os.path.join(out_dir, f"part_{file_number}.txt")
            with open(out_path, "wb") as cf:
                cf.write(chunk)
            file_number += 1
    await update.message.reply_text(
        f"✅ <b>Split Complete!</b>\n{DIVIDER}\n"
        f"📁 Folder: <code>{out_dir}/</code>\n"
        f"📊 Total files: <b>{file_number-1}</b>",
        parse_mode=ParseMode.HTML,
    )
    if filename.startswith("temp_combo"):
        os.remove(filename)

# ───────────────────────── Mode entry commands ─────────────────────────
async def cardclean_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user(user_id):
        await update.message.reply_text("⛔ No permission")
        return
    # If replied to a file, process directly
    if update.message.reply_to_message and update.message.reply_to_message.document:
        context.user_data["mode"] = "cardclean"
        await process_replied_file(update, context)
        return
    context.user_data["mode"] = "cardclean"
    await update.message.reply_text(
        "🧹 <b>Card Clean Mode</b>\n"
        f"{DIVIDER}\n"
        "📤 Card dump <code>.txt</code> ဖိုင်ကို <b>upload</b> လုပ်ပါ။\n\n"
        "💡 <i>သို့မဟုတ် ဖိုင်ကို <b>Reply</b> ထောက်ပြီး\n"
        "<code>/cardclean</code> ရိုက်လည်း ရပါတယ်။</i>",
        parse_mode=ParseMode.HTML,
    )

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
    if update.message.reply_to_message and update.message.reply_to_message.document:
        await process_replied_file(update, context)
        return
    await update.message.reply_text(
        f"✂️ <b>CN Split Mode</b>\n"
        f"{DIVIDER}\n"
        f"📤 Cards list <code>.txt</code> ဖိုင်ကို upload လုပ်ပါ\n"
        f"➜ <b>{number}</b> cards / file\n\n"
        "💡 <i>ဖိုင်ကို <b>Reply</b> ထောက်ပြီး\n"
        f"<code>/cn {number}</code> ရိုက်လည်း ရပါတယ်။</i>",
        parse_mode=ParseMode.HTML,
    )

async def clean_combo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user(user_id):
        await update.message.reply_text("⛔ No permission")
        return
    context.user_data["mode"] = "clean_combo"
    if update.message.reply_to_message and update.message.reply_to_message.document:
        await process_replied_file(update, context)
        return
    await update.message.reply_text(
        "🧽 <b>Clean Combo Mode</b>\n"
        f"{DIVIDER}\n"
        "📤 Combo <code>.txt</code> ဖိုင်ကို upload လုပ်ပါ။\n"
        "➜ Ads, @usernames, links တွေ ဖယ်ရှားပြီး\n"
        "   <code>email:pass</code> သီးသန့်ထုတ်ပေးမည်။\n\n"
        "💡 <i>ဖိုင်ကို <b>Reply</b> ထောက်ပြီး\n"
        "<code>/cleancombo</code> ရိုက်လည်း ရပါတယ်။</i>",
        parse_mode=ParseMode.HTML,
    )

# ───────────────────────── Card extractor ─────────────────────────
def extract_cards_from_text(content):
    patterns = [
        r"\b(\d{13,19})\s*[|:]\s*(\d{1,2})\s*[|:]\s*(\d{2,4})\s*[|:]\s*(\d{3,4})\b",
        r"\b(\d{13,19})\s*[|:]\s*(\d{1,2})\s*[|:]\s*(\d{2,4})\b",
    ]
    cards = []
    for pattern in patterns:
        for match in re.findall(pattern, content, re.IGNORECASE):
            if len(match) == 4:
                cards.append(f"{match[0]}|{match[1]}|{match[2]}|{match[3]}")
            elif len(match) == 3:
                cards.append(f"{match[0]}|{match[1]}|{match[2]}")
    return list(dict.fromkeys(cards))

# ───────────────────────── Document processing ─────────────────────────
async def process_replied_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the case where /command is used as a reply to a document."""
    await handle_document(update, context, from_reply=True)

async def handle_document(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    from_reply: bool = False,
):
    user_id = update.effective_user.id
    if not is_user(user_id):
        return

    if from_reply:
        doc = update.message.reply_to_message.document
    elif update.message.document:
        doc = update.message.document
    elif update.message.reply_to_message and update.message.reply_to_message.document:
        doc = update.message.reply_to_message.document
    else:
        await update.message.reply_text(
            "❌ <code>.txt</code> ဖိုင်တစ်ခု upload လုပ်ပါ။\n\n"
            "💡 <i>သို့မဟုတ် ဖိုင်ကို <b>Reply</b> ထောက်ပြီး\n"
            "command ရိုက်ပါ။</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    if not doc.file_name.endswith(".txt"):
        await update.message.reply_text("❌ <code>.txt</code> ဖိုင်သာ လက်ခံပါတယ်။", parse_mode=ParseMode.HTML)
        return

    file = await doc.get_file()
    file_path = f"temp_{user_id}.txt"
    await file.download_to_drive(file_path)

    mode = context.user_data.get("mode")

    if mode == "cardclean":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        cards = extract_cards_from_text(content)
        if not cards:
            await update.message.reply_text(
                "⚠️ <b>Cards မတွေ့ပါ</b>\n"
                f"{DIVIDER}\n"
                "Format: <code>4111111111111111|12|25|123</code>",
                parse_mode=ParseMode.HTML,
            )
        else:
            out_file = f"cleaned_{user_id}.txt"
            with open(out_file, "w", encoding="utf-8") as f:
                f.write("\n".join(cards))
            await update.message.reply_document(
                document=open(out_file, "rb"),
                filename="cleaned_cards.txt",
                caption=f"✅ <b>{len(cards)}</b> cards extracted\n{BRAND}",
                parse_mode=ParseMode.HTML,
            )
            os.remove(out_file)
        context.user_data["mode"] = None

    elif mode == "cn_split":
        number = context.user_data.get("cn_number", 100)
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [line.strip() for line in f if line.strip()]
        if not lines:
            await update.message.reply_text("⚠️ ဖိုင်ထဲမှာ ဘာမှမပါပါ။")
        else:
            out_dir = "cn_split_cards"
            os.makedirs(out_dir, exist_ok=True)
            total = len(lines)
            part = 1
            for i in range(0, total, number):
                batch = lines[i : i + number]
                out_path = os.path.join(out_dir, f"cards_part_{part}.txt")
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(batch))
                part += 1
            await update.message.reply_text(
                f"✅ <b>Split Complete!</b>\n{DIVIDER}\n"
                f"📊 Total: <b>{total}</b> cards\n"
                f"📁 Files: <b>{part-1}</b> in <code>{out_dir}/</code>",
                parse_mode=ParseMode.HTML,
            )
        context.user_data["mode"] = None

    elif mode == "clean_combo":
        cleaned = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                first_part = line.split()[0] if line.split() else line
                if ":" in first_part and ("@" in first_part or ".com" in first_part or ".net" in first_part):
                    cleaned.append(first_part)
                else:
                    match = re.search(
                        r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}:[^\s]+)",
                        line,
                    )
                    if match:
                        cleaned.append(match.group(1))
        cleaned = list(dict.fromkeys(cleaned))
        if not cleaned:
            await update.message.reply_text("⚠️ Combo မတွေ့ပါ။")
        else:
            out_file = f"clean_combo_{user_id}.txt"
            with open(out_file, "w", encoding="utf-8") as f:
                f.write("\n".join(cleaned))
            await update.message.reply_document(
                document=open(out_file, "rb"),
                filename="cleaned_combo.txt",
                caption=f"✅ <b>{len(cleaned)}</b> combos cleaned\n{BRAND}",
                parse_mode=ParseMode.HTML,
            )
            os.remove(out_file)
        context.user_data["mode"] = None

    else:
        await update.message.reply_text(
            "⚠️ <b>Command အရင်ရွေးပါ</b>\n"
            f"{DIVIDER}\n"
            "<code>/cardclean</code> • <code>/cn</code> • <code>/cleancombo</code>\n\n"
            "💡 <i>Tip: ဖိုင်ကို <b>Reply</b> ထောက်ပြီး\n"
            "command ရိုက်တာက ပိုမြန်ပါတယ်!</i>",
            parse_mode=ParseMode.HTML,
        )

    if os.path.exists(file_path):
        os.remove(file_path)

# ───────────────────────── Admin ─────────────────────────
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Admin only")
        return
    await update.message.reply_text(
        f"👑 <b>Admin Panel</b>\n{DIVIDER}\nUser management tools\n{DIVIDER}\n{BRAND}",
        reply_markup=admin_keyboard(),
        parse_mode=ParseMode.HTML,
    )

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
    except Exception:
        await update.message.reply_text("❌ <code>/done &lt;user_id&gt;</code> ပုံစံသုံးပါ။", parse_mode=ParseMode.HTML)
        return
    if action == "add":
        add_user(target)
        await update.message.reply_text(f"✅ User <code>{target}</code> added", parse_mode=ParseMode.HTML)
    elif action == "remove":
        if target == ADMIN_ID:
            await update.message.reply_text("❌ Admin ကိုမဖျက်ရ")
        else:
            remove_user(target)
            await update.message.reply_text(f"✅ User <code>{target}</code> removed", parse_mode=ParseMode.HTML)
    context.user_data["admin_action"] = None

# ───────────────────────── Main ─────────────────────────
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
    app.add_handler(CallbackQueryHandler(menu_callback))
    print("🤖 Bot is running... Developer by ThuYa")
    app.run_polling()

if __name__ == "__main__":
    main()

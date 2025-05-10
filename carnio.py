import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
    ContextTypes,
    CommandHandler,
)
from pymongo import MongoClient

# === Configuration ===
ADMIN_ID = 6999372290  # 🔁 Replace with your Telegram ID
BOT_TOKEN = "8006165946:AAFoIk1txo28CGOg1ekOrGuEyG-VkIfRj6c"

MONGO_URI = "mongodb+srv://codexkairnex:gm6xSxXfRkusMIug@cluster0.bplk1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["Micarnio"]
users_collection = db["users"]
message_logs = db["message_logs"]

# === Message Mapping ===
message_mapping = {}

# Save user ID if not already in database
def save_user(user_id: int):
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({"user_id": user_id})

# Log messages to MongoDB
def log_message(message: str, user_id: int, is_admin: bool):
    message_logs.insert_one({
        "user_id": user_id,
        "message": message,
        "is_admin": is_admin,
        "timestamp": asyncio.get_event_loop().time()
    })

# Get all user IDs from database
def get_all_user_ids():
    return [user["user_id"] for user in users_collection.find()]

# === Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id)
    await update.message.reply_text("Hi! Send me a message and my admin will see it.")
    log_message("User started the conversation.", user.id, False)

async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    message = update.message

    save_user(user.id)
    forwarded = await context.bot.forward_message(
        chat_id=ADMIN_ID,
        from_chat_id=message.chat_id,
        message_id=message.message_id
    )
    message_mapping[forwarded.message_id] = user.id
    log_message(f"User message forwarded: {message.text}", user.id, False)

async def reply_from_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    if update.message.reply_to_message:
        replied_msg_id = update.message.reply_to_message.message_id
        original_user_id = message_mapping.get(replied_msg_id)

        if original_user_id:
            try:
                await context.bot.send_message(chat_id=original_user_id, text=update.message.text)
                log_message(f"Admin replied: {update.message.text}", original_user_id, True)
            except Exception as e:
                await update.message.reply_text(f"Failed to send message to user: {e}")
                log_message(f"Failed admin reply: {str(e)}", ADMIN_ID, True)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if context.args:
        text = " ".join(context.args)
    elif update.message.reply_to_message:
        text = update.message.reply_to_message.text
    else:
        await update.message.reply_text("Please provide a message or reply to one.")
        return

    user_ids = get_all_user_ids()
    success, failed = 0, 0

    for uid in user_ids:
        try:
            await context.bot.send_message(chat_id=uid, text=text)
            success += 1
            log_message(f"Broadcast message sent: {text}", uid, True)
        except:
            failed += 1

    await update.message.reply_text(f"Broadcast sent.\n✅ Success: {success}\n❌ Failed: {failed}")

# === Bot Setup ===
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID) & filters.REPLY, reply_from_admin))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.User(ADMIN_ID), forward_to_admin))

    await app.initialize()
    print("Bot initialized.")
    await app.start()
    print("Bot started.")
    await app.updater.start_polling()
    print("Polling started.")

# === Runner ===
if __name__ == "__main__":
    try:
        asyncio.run(main())  # Properly run the main function
    except Exception as e:
        print(f"Error starting bot: {e}")

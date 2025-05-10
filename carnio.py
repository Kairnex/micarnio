from telegram import Update, Message
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler
from pymongo import MongoClient

# Replace with your Telegram user ID and Bot token
ADMIN_ID = 6999372290  # 👈 Replace with your ID
BOT_TOKEN = "8006165946:AAFoIk1txo28CGOg1ekOrGuEyG-VkIfRj6c"

# MongoDB setup
MONGO_URI = "mongodb+srv://codexkairnex:gm6xSxXfRkusMIug@cluster0.bplk1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"  # or use your MongoDB Atlas URI
client = MongoClient(MONGO_URI)
db = client["Micarnio"]
users_collection = db["users"]

# A dictionary to map forwarded message IDs to original sender IDs
message_mapping = {}

# Save user ID if not already in database
def save_user(user_id: int):
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({"user_id": user_id})

# Get all user IDs from database
def get_all_user_ids():
    return [user["user_id"] for user in users_collection.find()]

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Send me a message and my admin will see it.")

# Handle all user messages and forward them to the admin
async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    message = update.message

    save_user(user.id)  # Save user ID to MongoDB

    # Forward message to admin
    forwarded = await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=message.chat_id, message_id=message.message_id)
    message_mapping[forwarded.message_id] = user.id

# Handle replies from admin
async def reply_from_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    if update.message.reply_to_message and update.message.reply_to_message.message_id in message_mapping:
        original_user_id = message_mapping[update.message.reply_to_message.message_id]
        try:
            await context.bot.send_message(chat_id=original_user_id, text=update.message.text)
        except Exception as e:
            await update.message.reply_text(f"Failed to send message to user: {e}")

# Broadcast command
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
        except:
            failed += 1

    await update.message.reply_text(f"Broadcast sent.\n✅ Success: {success}\n❌ Failed: {failed}")

# Main function
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID) & filters.REPLY, reply_from_admin))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.User(ADMIN_ID), forward_to_admin))

    print("Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

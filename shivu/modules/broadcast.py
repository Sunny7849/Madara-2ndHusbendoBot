from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ChatMemberHandler

from shivu import application, user_collection, top_global_groups_collection, channels_collection

OWNER_ID = 8156600797

# STEP 1: Start Broadcast Command
async def broadcast(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    await update.message.reply_text("Send the content that you want to share.")
    context.user_data["awaiting_broadcast_content"] = True

# STEP 2: Capture Content
async def capture_broadcast_content(update: Update, context: CallbackContext):
    if context.user_data.get("awaiting_broadcast_content", False):
        context.user_data["broadcast_content"] = update.message
        context.user_data["awaiting_broadcast_content"] = False

        keyboard = [
            [InlineKeyboardButton("1. Personal", callback_data="broadcast_personal")],
            [InlineKeyboardButton("2. Group Chat", callback_data="broadcast_group")],
            [InlineKeyboardButton("3. Channel", callback_data="broadcast_channel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Select where to broadcast:", reply_markup=reply_markup)

# STEP 3: Handle Button Press
async def handle_broadcast_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    content = context.user_data.get("broadcast_content")
    if not content:
        await query.edit_message_text("No content found. Please start again using /broadcast.")
        return

    if query.data == "broadcast_personal":
        target_ids = await user_collection.distinct("id")
    elif query.data == "broadcast_group":
        target_ids = await top_global_groups_collection.distinct("group_id")
    elif query.data == "broadcast_channel":
        target_ids = await channels_collection.distinct("channel_id")
    else:
        await query.edit_message_text("Invalid option selected.")
        return

    failed = 0
    for chat_id in target_ids:
        try:
            await context.bot.forward_message(
                chat_id=chat_id,
                from_chat_id=content.chat_id,
                message_id=content.message_id
            )
        except Exception as e:
            print(f"Failed to send to {chat_id}: {e}")
            failed += 1

    await query.edit_message_text(
        f"Sensei I've completed the broadcast. If you have any other work you need done, let me know🎐\n\nFailed to send to {failed} chats."
    )

# STEP 4: Track Channel Additions Automatically
async def track_channel_addition(update: Update, context: CallbackContext):
    chat = update.my_chat_member.chat
    new_status = update.my_chat_member.new_chat_member.status

    if chat.type == "channel" and new_status in ["administrator", "member"]:
        await channels_collection.update_one(
            {"channel_id": chat.id},
            {"$set": {"channel_id": chat.id}},
            upsert=True
        )
        print(f"Added channel to DB: {chat.title} ({chat.id})")

# HANDLER REGISTRATION
application.add_handler(CommandHandler("broadcast", broadcast, block=False))
application.add_handler(MessageHandler(filters.ALL, capture_broadcast_content, block=False))
application.add_handler(CallbackQueryHandler(handle_broadcast_selection))
application.add_handler(ChatMemberHandler(track_channel_addition, chat_member_types=["my_chat_member"]))

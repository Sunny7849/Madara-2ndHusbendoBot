from pyrogram import filters
from pyrogram.types import Message
from shivu import shivuu, collection, CHARA_CHANNEL_ID
import os
import requests
from asyncio import Lock

# Lock for ID safety
id_lock = Lock()
active_ids = set()

# Rarity Map
rarity_map = {
    1: "⚪ Common", 2: "🟣 Rare", 3: "🟢 Medium", 4: "🟡 Legendary", 5: "💮 Special Edition",
    6: "🔮 Limited Edition", 7: "🎐 Celestial Beauty", 8: "🪽 Divine Edition", 
    9: "💦 Wet Elegance", 10: "🎴 Cosplay"
}

# Format error text
WRONG_FORMAT_TEXT = """Wrong ❌ format... eg: /wadd reply to photo muzan-kibutsuji Demon-slayer 3

Format: /wadd reply character-name anime-name rarity-number

Rarity Map:
1: ⚪ Common
2: 🟣 Rare
3: 🟢 Medium
4: 🟡 Legendary
5: 💮 Special Edition
6: 🔮 Limited Edition
7: 🎐 Celestial Beauty
8: 🪽 Divine Edition
9: 💦 Wet Elegance
10: 🎴 Cosplay
"""

# Catbox Upload Function
def upload_to_catbox(file_path):
    url = "https://catbox.moe/user/api.php"
    payload = {'reqtype': 'fileupload'}
    with open(file_path, 'rb') as f:
        files = {'fileToUpload': f}
        response = requests.post(url, data=payload, files=files)
    if response.status_code == 200:
        return response.text.strip()
    else:
        raise Exception("Catbox upload failed.")

# ID Generator
async def find_available_id():
    async with id_lock:
        cursor = collection.find().sort('id', 1)
        ids = [doc['id'] for doc in await cursor.to_list(length=None)]
        for i in range(1, max(map(int, ids), default=0) + 2):
            cid = str(i).zfill(2)
            if cid not in ids and cid not in active_ids:
                active_ids.add(cid)
                return cid
        return str(max(map(int, ids), default=0) + 1).zfill(2)

# /wadd Command - Upload
@shivuu.on_message(filters.command("wadd") & filters.user([7756901810, 7640076990, 7885908019, 7378476666]))
async def upload_character(client, message: Message):
    reply = message.reply_to_message
    if not reply or not (reply.photo or reply.document):
        return await message.reply_text("Please reply to a photo or document.")

    args = message.text.split()
    if len(args) != 4:
        return await message.reply_text(WRONG_FORMAT_TEXT)

    try:
        name = args[1].replace("-", " ").title()
        anime = args[2].replace("-", " ").title()
        rarity_num = int(args[3])
        if rarity_num not in rarity_map:
            return await message.reply_text("Invalid rarity number (1-10 only).")
        rarity = rarity_map[rarity_num]
    except:
        return await message.reply_text(WRONG_FORMAT_TEXT)

    try:
        available_id = await find_available_id()
        character = {
            'name': name,
            'anime': anime,
            'rarity': rarity,
            'id': available_id
        }

        msg = await message.reply("<ᴘʀᴏᴄᴇꜱꜱɪɴɢ>...")
        path = await reply.download()
        url = upload_to_catbox(path)
        character['img_url'] = url

        await collection.insert_one(character)

        await client.send_photo(
            chat_id=CHARA_CHANNEL_ID,
            photo=url,
            caption=(
                f"Character Name: {name}\n"
                f"Anime Name: {anime}\n"
                f"Rarity: {rarity}\n"
                f"ID: {available_id}\n"
                f"Added by [{message.from_user.first_name}](tg://user?id={message.from_user.id})"
            )
        )
        await msg.edit(f"✅ CHARACTER ADDED\nID: `{available_id}`")

    except Exception as e:
        await message.reply_text(f"Upload failed: {e}")

    finally:
        if os.path.exists(path):
            os.remove(path)
        async with id_lock:
            active_ids.discard(available_id)


# /wupdate Command - Update character
@shivuu.on_message(filters.command("wupdate") & filters.user([7756901810, 7640076990, 7885908019, 7378476666]))
async def update_character(client, message: Message):
    reply = message.reply_to_message
    if not reply or not (reply.photo or reply.document):
        return await message.reply("Reply to a new image of the character.")

    args = message.text.split()
    if len(args) != 2:
        return await message.reply("Use: /wupdate <character_id> (as reply to image)")

    cid = args[1]
    character = await collection.find_one({"id": cid})
    if not character:
        return await message.reply("Character ID not found.")

    try:
        msg = await message.reply("Updating image...")
        path = await reply.download()
        url = upload_to_catbox(path)

        await collection.update_one({"id": cid}, {"$set": {"img_url": url}})
        await msg.edit("✅ Character image updated.")

    except Exception as e:
        await message.reply(f"Update failed: {e}")

    finally:
        if os.path.exists(path):
            os.remove(path)


# /wdel Command - Delete character
@shivuu.on_message(filters.command("wdel") & filters.user([7756901810, 7640076990, 7885908019, 7378476666]))
async def delete_character(client, message: Message):
    args = message.text.split()
    if len(args) != 2:
        return await message.reply("Use: /wdel <character_id>")

    cid = args[1]
    result = await collection.delete_one({"id": cid})
    if result.deleted_count == 0:
        return await message.reply("Character not found.")
    
    await message.reply(f"✅ Character `{cid}` deleted.")

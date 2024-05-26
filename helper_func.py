import base64
import re
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus
from config import FORCE_SUB_CHANNEL, ADMINS
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.errors import FloodWait

# Configure logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def is_subscribed(filter, client, update):
    if not FORCE_SUB_CHANNEL:
        logger.info("FORCE_SUB_CHANNEL is not set. Skipping subscription check.")
        return True
    user_id = update.from_user.id
    if user_id in ADMINS:
        logger.info(f"User {user_id} is an admin. Skipping subscription check.")
        return True
    try:
        member = await client.get_chat_member(chat_id=FORCE_SUB_CHANNEL, user_id=user_id)
        if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]:
            logger.warning(f"User {user_id} is not a valid member of the channel.")
            return False
        logger.info(f"User {user_id} is subscribed to the channel.")
        return True
    except UserNotParticipant:
        logger.warning(f"User {user_id} is not a participant of the channel.")
        return False
    except Exception as e:
        logger.error(f"Error checking subscription for user {user_id}: {e}")
        return False

async def encode(string):
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    base64_string = base64_bytes.decode("ascii").strip("=")
    return base64_string

async def decode(base64_string):
    base64_string = base64_string.strip("=")
    base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
    string_bytes = base64.urlsafe_b64decode(base64_bytes)
    string = string_bytes.decode("ascii")
    return string

async def get_messages(client, message_ids):
    messages = []
    total_messages = 0
    while total_messages != len(message_ids):
        temp_ids = message_ids[total_messages:total_messages+200]
        try:
            msgs = await client.get_messages(chat_id=client.db_channel.id, message_ids=temp_ids)
        except FloodWait as e:
            logger.warning(f"FloodWait error: Sleeping for {e.x} seconds.")
            await asyncio.sleep(e.x)
            msgs = await client.get_messages(chat_id=client.db_channel.id, message_ids=temp_ids)
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            break
        total_messages += len(temp_ids)
        messages.extend(msgs)
    return messages

async def get_message_id(client, message):
    if message.forward_from_chat:
        if message.forward_from_chat.id == client.db_channel.id:
            return message.forward_from_message_id
        return 0
    elif message.forward_sender_name:
        return 0
    elif message.text:
        pattern = r'https://t.me/(?:c/)?(\d+)/(\d+)'
        matches = re.match(pattern, message.text)
        if not matches:
            return 0
        channel_id = matches.group(1)
        msg_id = int(matches.group(2))
        if channel_id.isdigit():
            if f"-100{channel_id}" == str(client.db_channel.id):
                return msg_id
        else:
            if channel_id == client.db_channel.username:
                return msg_id
    return 0

def get_readable_time(seconds: int) -> str:
    count = 0
    up_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    time_list.reverse()
    for i, time in enumerate(time_list):
        up_time += f"{time}{time_suffix_list[i]}{' ' if i < len(time_list) - 1 else ''}"
    return up_time

subscribed = filters.create(is_subscribed)

# Example main function to run the bot
async def main():
    app = Client("my_bot")
    
    @app.on_message(subscribed)
    async def handle_message(client, message):
        logger.info(f"Received message from {message.from_user.id}")

    await app.start()
    logger.info("Bot started.")
    await app.idle()

if __name__ == "__main__":
    asyncio.run(main())

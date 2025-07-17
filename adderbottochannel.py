import asyncio
from telegram import Bot

async def get_channel_id():
    bot = Bot(token="7680961829:AAH80RDjOAsJUbFihPO3Az9mOgQO57pLe2M")
    
    # Send a test message to your channel
    # Then check the response to get the chat ID
    try:
        # Replace with your channel username
        chat = await bot.get_chat("@bestdeal307")
        print(f"Channel ID: {chat.id}")
        return chat.id
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure your bot is added to the channel as admin")

# Run this once to get your channel ID
if __name__ == "__main__":
    asyncio.run(get_channel_id())

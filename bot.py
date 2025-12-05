import os

import discord
from dotenv import load_dotenv

# Load variables from .env into the process environment
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
HONEYPOT_GUILD_ID = int(os.getenv("HONEYPOT_GUILD_ID", "0"))
HONEYPOT_CHANNEL_ID = int(os.getenv("HONEYPOT_CHANNEL_ID", "0"))
SAFE_USER_ID = int(os.getenv("SAFE_USER_ID", "0"))

if not TOKEN or not HONEYPOT_GUILD_ID or not HONEYPOT_CHANNEL_ID:
    raise RuntimeError(
        "DISCORD_TOKEN, HONEYPOT_GUILD_ID, and HONEYPOT_CHANNEL_ID must be set"
    )

# Intents control which events your bot receives.
# We need guilds + messages; message_content is not strictly required for this logic,
# but enabling it is fine if you already have it enabled in the Developer Portal.
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True  # requires the privileged intent to be enabled in the portal

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")
    print(f"Honeypot guild: {HONEYPOT_GUILD_ID}, channel: {HONEYPOT_CHANNEL_ID}")


@client.event
async def on_message(message: discord.Message):
    # Ignore bots, including ourselves
    if message.author.bot:
        return

    # We only care about guild text messages
    if message.guild is None:
        return

    # Only act in the configured honeypot guild and channel
    if message.guild.id != HONEYPOT_GUILD_ID:
        return

    if message.channel.id != HONEYPOT_CHANNEL_ID:
        return

    guild = message.guild
    user = message.author

    if user.id == SAFE_USER_ID:
        return

    print(
        f"Honeypot triggered by {user} ({user.id}) "
        f"in guild {guild.id} channel {message.channel.id}"
    )

    # Ban the user and delete up to 7 days of their recent messages.
    # delete_message_days is capped at 7 by Discord’s API.
    try:
        await guild.ban(
            user,
            reason="Honeypot channel triggered",
            delete_message_days=7,
        )
    except discord.Forbidden as e:
        # Missing permissions (e.g. bot role below the user’s highest role)
        print(f"Failed to ban {user} ({user.id}): missing permissions: {e}")
        return
    except discord.HTTPException as e:
        # Some other HTTP error
        print(f"Failed to ban {user} ({user.id}): HTTP error: {e}")
        return

    # After a successful ban, post a message in the honeypot channel tagging them.
    try:
        await message.channel.send(
            f"{user.mention} has been banned for triggering the honeypot."
        )
    except discord.HTTPException as e:
        print(f"Failed to send honeypot notification: {e}")


if __name__ == "__main__":
    client.run(TOKEN)

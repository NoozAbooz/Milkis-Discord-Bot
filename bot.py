import os
import re
import json
import discord
import asyncio
import threading
from discord.ext import commands, tasks
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Get configuration from environment variables
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
ADMIN_ROLE_ID = int(os.getenv('ADMIN_ROLE_ID'))
ROLE_TO_ASSIGN_ID = int(os.getenv('ROLE_TO_ASSIGN_ID'))
STATUS_REGEX = os.getenv('STATUS_REGEX')
COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '!')
EMBED_TITLE = os.getenv('EMBED_TITLE', 'Role Verification')
EMBED_DESCRIPTION = os.getenv('EMBED_DESCRIPTION', 'React to this message to get verified if your status contains the required text.')
REACTION_EMOJI = os.getenv('REACTION_EMOJI')
WATCHLIST_CHECK_INTERVAL = int(os.getenv('WATCHLIST_CHECK_INTERVAL', 5))
WATCHLIST_FILE = os.getenv('WATCHLIST_FILE', 'verified_users.json')

# Setup intents to access all the data we need
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

# Create bot instance
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# Watchlist file lock to prevent concurrent access
file_lock = threading.Lock()

# Create watchlist for verified users
verified_users = set()

def load_watchlist():
    """Load watchlist from file"""
    global verified_users
    try:
        with file_lock:
            if os.path.exists(WATCHLIST_FILE):
                with open(WATCHLIST_FILE, 'r') as f:
                    data = json.load(f)
                    # Convert list of lists to set of tuples
                    verified_users = set(tuple(item) for item in data)
                print(f"Loaded {len(verified_users)} users from watchlist file")
            else:
                verified_users = set()
                print("No existing watchlist file found, starting with empty watchlist")
    except Exception as e:
        print(f"Error loading watchlist: {e}")
        verified_users = set()

def save_watchlist():
    """Save watchlist to file"""
    try:
        with file_lock:
            # Convert set of tuples to list of lists for JSON serialization
            data = [list(item) for item in verified_users]
            
            # Use atomic write pattern (write to temp file, then rename)
            temp_file = f"{WATCHLIST_FILE}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(data, f)
            
            # Atomic replace
            if os.path.exists(WATCHLIST_FILE):
                os.replace(temp_file, WATCHLIST_FILE)
            else:
                os.rename(temp_file, WATCHLIST_FILE)
    except Exception as e:
        print(f"Error saving watchlist: {e}")

def add_to_watchlist(guild_id, user_id):
    """Add a user to the watchlist and save to file"""
    global verified_users
    verified_users.add((guild_id, user_id))
    save_watchlist()

def remove_from_watchlist(items_to_remove):
    """Remove users from the watchlist and save to file"""
    global verified_users
    if items_to_remove:
        verified_users.difference_update(items_to_remove)
        save_watchlist()
        print(f"Removed {len(items_to_remove)} users from watchlist")

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    
    # Load the watchlist from file
    load_watchlist()
    
    # Update the watchlist with users who already have the role
    users_added = 0
    for guild in bot.guilds:
        role = guild.get_role(ROLE_TO_ASSIGN_ID)
        if role:
            for member in role.members:
                if (guild.id, member.id) not in verified_users:
                    verified_users.add((guild.id, member.id))
                    users_added += 1
    
    if users_added > 0:
        print(f"Added {users_added} new users to watchlist")
        save_watchlist()
    
    print(f"Initialized watchlist with {len(verified_users)} users")
    
    # Start both task loops after the bot is ready and the event loop is running
    check_watchlist.start()
    backup_watchlist.start()

@bot.command(name='send_statusrole_embed')
async def verify(ctx):
    """Admin command to send verification embed"""
    # Check if the user has admin role
    is_admin = False
    for role in ctx.author.roles:
        if role.id == ADMIN_ROLE_ID:
            is_admin = True
            break
    
    if not is_admin:
        await ctx.send("You don't have permission to use this command.")
        return
    
    # Create and send embed
    embed = discord.Embed(
        title=EMBED_TITLE,
        description=EMBED_DESCRIPTION,
        color=discord.Color.blue()
    )
    
    embed.set_footer(text=f"Provided by {bot.user.name} bot")
    
    message = await ctx.send(embed=embed)
    await message.add_reaction(REACTION_EMOJI)

@bot.event
async def on_raw_reaction_add(payload):
    """Handle reactions to the verification message"""
    if payload.user_id == bot.user.id:
        return  # Ignore bot's own reactions
    
    # Get necessary objects
    channel = await bot.fetch_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    
    # Check if the reaction is on a verification embed from the bot
    if message.author != bot.user or not message.embeds or message.embeds[0].title != EMBED_TITLE:
        return
    
    # Check if the reaction emoji matches
    if str(payload.emoji) != REACTION_EMOJI:
        return
    
    # Check member's status
    status_text = ""
    for activity in member.activities:
        if isinstance(activity, discord.CustomActivity) and activity.name:
            status_text = activity.name
            break
    
    # If status matches regex, assign role
    error_emoji = "❌"
    success_emoji = "✅"
    if re.search(STATUS_REGEX, status_text):
        role = guild.get_role(ROLE_TO_ASSIGN_ID)
        if role:
            await message.remove_reaction(payload.emoji, member)

            await member.add_roles(role)
            
            # Add user to watchlist with file save
            add_to_watchlist(guild.id, member.id)
            
            # Show success reaction
            await message.add_reaction(success_emoji)
            await message.clear_reaction(REACTION_EMOJI)
            await asyncio.sleep(1)
            await message.add_reaction(REACTION_EMOJI)
            await message.clear_reaction(success_emoji)
    else:
        # Remove their reaction if they don't qualify
        await message.remove_reaction(payload.emoji, member)
        
        await message.add_reaction(error_emoji)
        await message.clear_reaction(REACTION_EMOJI)
        await asyncio.sleep(1)
        await message.add_reaction(REACTION_EMOJI)
        await message.clear_reaction(error_emoji)

@tasks.loop(seconds=WATCHLIST_CHECK_INTERVAL)
async def check_watchlist():
    """Check if users in the watchlist still have a valid status"""
    #print(f"Checking watchlist: {len(verified_users)} users")
    
    users_to_remove = set()
    
    for guild_id, user_id in verified_users:
        guild = bot.get_guild(guild_id)
        if not guild:
            users_to_remove.add((guild_id, user_id))
            continue
            
        member = guild.get_member(user_id)
        if not member:
            users_to_remove.add((guild_id, user_id))
            continue
        
        role = guild.get_role(ROLE_TO_ASSIGN_ID)
        if not role or role not in member.roles:
            users_to_remove.add((guild_id, user_id))
            continue
            
        # Check member's current status
        status_text = ""
        for activity in member.activities:
            if isinstance(activity, discord.CustomActivity) and activity.name:
                status_text = activity.name
                break
                
        # If status no longer matches the regex, remove the role
        if not re.search(STATUS_REGEX, status_text):
            try:
                await member.remove_roles(role)
                print(f"Removed role from {member.display_name} ({member.id}) - Status no longer matches")
                users_to_remove.add((guild_id, user_id))
            except Exception as e:
                print(f"Error removing role from {member.id}: {e}")
    
    # Update the watchlist by removing users who no longer qualify
    if users_to_remove:
        remove_from_watchlist(users_to_remove)

@tasks.loop(minutes=30)
async def backup_watchlist():
    """Periodically backup the watchlist file"""
    save_watchlist()
    print(f"Watchlist backup saved: {len(verified_users)} users")

@check_watchlist.before_loop
async def before_check_watchlist():
    """Wait for the bot to be ready before starting the loop"""
    await bot.wait_until_ready()

@backup_watchlist.before_loop
async def before_backup_watchlist():
    """Wait for the bot to be ready before starting the backup loop"""
    await bot.wait_until_ready()

# Run the bot
bot.run(TOKEN)
import os
import re
import discord
import asyncio
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

# Setup intents to access all the data we need
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

# Create bot instance
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# Create watchlist for verified users
verified_users = set()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    
    # Initialize the watchlist with users who already have the role
    for guild in bot.guilds:
        role = guild.get_role(ROLE_TO_ASSIGN_ID)
        if role:
            for member in role.members:
                verified_users.add((guild.id, member.id))
    
    print(f"Initialized watchlist with {len(verified_users)} users")
    
    # Start the periodic status check
    check_watchlist.start()

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
            
            # Add user to watchlist
            verified_users.add((guild.id, member.id))
            
            # Fixed the typo here
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
    verified_users.difference_update(users_to_remove)
    
    if users_to_remove:
        print(f"Removed {len(users_to_remove)} users from watchlist")

@check_watchlist.before_loop
async def before_check_watchlist():
    """Wait for the bot to be ready before starting the loop"""
    await bot.wait_until_ready()

# Run the bot
bot.run(TOKEN)
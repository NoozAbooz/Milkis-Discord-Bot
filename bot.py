import os
import re
import discord
import asyncio
from discord.ext import commands
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
REACTION_EMOJI = os.getenv('REACTION_EMOJI', '✅')

# Setup intents to access all the data we need
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

# Create bot instance
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command(name='verify')
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
    
    embed.set_footer(text=f"Verification managed by {bot.user.name}")
    
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

            await message.add_reaction(success_emoji_emoji)
            await message.clear_reaction(REACTION_EMOJI)
            await asyncio.sleep(1)
            await message.add_reaction(REACTION_EMOJI)
            await message.clear_reaction(success_emoji)

            #await channel.send(f"{member.mention} has been verified and given the {role.name} role.", delete_after=10)
    else:
        # Remove their reaction if they don't qualify
        await message.remove_reaction(payload.emoji, member)
        
        await message.add_reaction(error_emoji)
        await message.clear_reaction(REACTION_EMOJI)
        await asyncio.sleep(1)
        await message.add_reaction(REACTION_EMOJI)
        await message.clear_reaction(error_emoji)
		
        #await channel.send(f"{member.mention}, your status doesn't contain the required text.", delete_after=10)

# Run the bot
bot.run(TOKEN)
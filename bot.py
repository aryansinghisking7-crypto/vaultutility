import discord
from discord.ext import commands, tasks
import qrcode
import io
import requests
import os

# ====== CONFIG ======
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")  # Reads from Render env vars
PREFIX = "$"

# Storage - resets on restart. Use a DB later if you need persistence
user_data = {
    "upi_id": None,
    "ltc_address": None
}

# ====== BOT SETUP ======
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ====== COOLDOWN ERROR HANDLER ======
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Slow down bro 💀 Try again in {error.retry_after:.1f}s", delete_after=3)
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have perms for that ❌", delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing argument. Usage: `{PREFIX}{ctx.command} {ctx.command.signature}`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Invalid argument. Tag a user or use a valid ID/number.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # ignore unknown commands
    else:
        print(f"Error: {error}")

# ====== UPI COMMANDS ======
@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def setupi(ctx, *, upi_id: str):
    """Set UPI ID. Usage: $setupi yourupi@bank"""
    user_data["upi_id"] = upi_id
    embed = discord.Embed(title="UPI ID Saved ✅", description=f"UPI set to: `{upi_id}`", color=0x00ff00)
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def upi(ctx):
    """Show UPI with QR. Usage: $upi"""
    if not user_data["upi_id"]:
        await ctx.send("No UPI ID set. Use `$setupi yourupi@bank` first.")
        return
    
    upi_string = f"upi://pay?pa={user_data['upi_id']}&pn=Payment"
    qr = qrcode.make(upi_string)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)
    
    embed = discord.Embed(title="

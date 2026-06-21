import discord
import os
import qrcode
import io
import json
import requests
import time
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='$', intents=intents, help_command=None)

# Persistent storage
try:
    with open('data.json', 'r') as f:
        user_data = json.load(f)
except FileNotFoundError:
    user_data = {}

cooldowns = {}
COOLDOWN_TIME = 5

def save_data():
    with open('data.json', 'w') as f:
        json.dump(user_data, f)

def check_cooldown(user_id, command):
    now = time.time()
    if user_id not in cooldowns:
        cooldowns[user_id] = {}
    last = cooldowns[user_id].get(command, 0)
    if now - last < COOLDOWN_TIME:
        return COOLDOWN_TIME - (now - last)
    cooldowns[user_id][command] = now
    return 0

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def help(ctx):
    """Shows all commands"""
    embed = discord.Embed(title="Zyro Utility Bot", color=0x2b2d31)
    embed.add_field(name="Payment", value="`$setupi <upi_id>` - Save your UPI ID\n`$upi <amount>` - Generate UPI QR\n`$setltc <address>` - Save LTC address\n`$ltc` - Show your LTC address\n`$checkbalance <address>` - Check LTC balance", inline=False)
    embed.add_field(name="Moderation", value="`$purge <1-100>` - Delete messages\n`$kick @user [reason]` - Kick member\n`$ban @user [reason]` - Ban member", inline=False)
    embed.add_field(name="Info", value="`$ping` - Bot latency\n`$help` - This menu", inline=False)
    embed.set_footer(text="Cooldown: 5s per command")
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    cd = check_cooldown(ctx.author.id, 'ping')
    if cd > 0: return await ctx.send(f'Slow down. {cd:.1f}s left.')
    await ctx.send(f'Pong! `{round(bot.latency * 1000)}ms`')

@bot.command()
async def setupi(ctx, upi_id: str):
    """Save your UPI ID. Usage: $setupi name@upi"""
    uid = str(ctx.author.id)
    user_data[uid] = user_data.get(uid, {})
    user_data[uid]['upi'] = upi_id
    save_data()
    embed = discord.Embed(description=f'UPI ID saved as `{upi_id}`', color=0x00ff00)
    await ctx.send(embed=embed)

@bot.command()
async def upi(ctx, amount: float):
    """Generate UPI QR for payment. Usage: $upi 250"""
    cd = check_cooldown(ctx.author.id, 'upi')
    if cd > 0: return await ctx.send(f'QR cooldown: {cd:.1f}s')

    uid = str(ctx.author.id)
    if uid not in user_data or 'upi' not in user_data[uid]:
        return await ctx.send('Set your UPI first: `$setupi yourupi@bank`')

    upi_id = user_data[uid]['upi']
    upi_link = f'upi://pay?pa={upi_id}&pn=Payment&am={amount}&cu=INR'

    img = qrcode.make(upi_link)
    with io.BytesIO() as buf:
        img.save(buf, 'PNG')
        buf.seek(0)
        embed = discord.Embed(title=f'Pay ₹{amount}', description=f'UPI: `{upi_id}`', color=0x5865f2)
        embed.set_image(url="attachment://upi.png")
        await ctx.send(embed=embed, file=discord.File(buf, 'upi.png'))

@bot.command()
async def setltc(ctx, address: str):
    """Save your LTC address. Usage: $setltc L..."""
    uid = str(ctx.author.id)
    user_data[uid] = user_data.get(uid, {})
    user_data[uid]['ltc'] = address
    save_data()
    embed = discord.Embed(description=f'LTC address saved: `{address}`', color=0x00ff00)
    await ctx.send(embed=embed)

@bot.command()
async def ltc(ctx):
    """Show your saved LTC address"""
    cd = check_cooldown(ctx.author.id, 'ltc')
    if cd > 0: return await ctx.send(f'Cooldown: {cd:.1f}s')

    uid = str(ctx.author.id)
    addr = user_data.get(uid, {}).get('ltc')
    if not addr:
        return await ctx.send('No LTC set. Use `$setltc address`')

    embed = discord.Embed(title="Your LTC Address", description=f'`{addr}`', color=0x345d9d)
    await ctx.send(embed=embed)

@bot.command()
async def checkbalance(ctx, address: str):
    """Check LTC balance of any address. Usage: $checkbalance L...

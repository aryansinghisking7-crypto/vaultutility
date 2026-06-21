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
    
    embed = discord.Embed(title="Scan to Pay", description=f"UPI ID: `{user_data['upi_id']}`", color=0x5865F2)
    file = discord.File(buffer, filename="upi_qr.png")
    embed.set_image(url="attachment://upi_qr.png")
    await ctx.send(embed=embed, file=file)

# ====== LTC COMMANDS ======
@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def setltc(ctx, *, address: str):
    """Set LTC address. Usage: $setltc Laddress"""
    if not (address.startswith("L") or address.startswith("M") or address.startswith("ltc1")):
        await ctx.send("That doesn't look like a valid LTC address ❌")
        return
    user_data["ltc_address"] = address
    embed = discord.Embed(title="LTC Address Saved ✅", description=f"LTC set to: `{address}`", color=0x00ff00)
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def ltc(ctx):
    """Show saved LTC address. Usage: $ltc"""
    if not user_data["ltc_address"]:
        await ctx.send("No LTC address set. Use `$setltc Laddress` first.")
        return
    embed = discord.Embed(title="LTC Address", description=f"`{user_data['ltc_address']}`", color=0x345D9D)
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def checkbalance(ctx, address: str):
    """Check LTC balance of any address. Usage: $checkbalance Laddress"""
    try:
        url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}/balance"
        r = requests.get(url, timeout=5).json()
        if "error" in r:
            await ctx.send("Invalid address or API error ❌")
            return
        balance = r["balance"] / 100000000  # satoshi to LTC
        embed = discord.Embed(title="LTC Balance", color=0x345D9D)
        embed.add_field(name="Address", value=f"`{address}`", inline=False)
        embed.add_field(name="Balance", value=f"`{balance:.8f} LTC`", inline=False)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send("API error or timeout. Try again later.")
        print(e)

# ====== MOD COMMANDS ======
@bot.command()
@commands.has_permissions(manage_messages=True)
@commands.cooldown(1, 5, commands.BucketType.user)
async def purge(ctx, amount: int):
    """Delete messages. Usage: $purge 10"""
    if amount > 100:
        await ctx.send("Max 100 messages at once.")
        return
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"Deleted {len(deleted)-1} messages ✅", delete_after=3)

@bot.command()
@commands.has_permissions(kick_members=True)
@commands.cooldown(1, 5, commands.BucketType.user)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    """Kick a member. Usage: $kick @user reason"""
    await member.kick(reason=reason)
    embed = discord.Embed(title="Member Kicked", description=f"{member.mention} was kicked.\nReason: {reason}", color=0xff0000)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(ban_members=True)
@commands.cooldown(1, 5, commands.BucketType.user)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    """Ban a member. Usage: $ban @user reason"""
    await member.ban(reason=reason)
    embed = discord.Embed(title="Member Banned", description=f"{member.mention} was banned.\nReason: {reason}", color=0xff0000)
    await ctx.send(embed=embed)

# ====== UTILITY ======
@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def ping(ctx):
    """Check bot latency. Usage: $ping"""
    await ctx.send(f"Pong! `{round(bot.latency * 1000)}ms`")

@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def help(ctx):
    """Show all commands. Usage: $help"""
    embed = discord.Embed(title="Zyro Utility Commands", color=0x5865F2)
    embed.add_field(name="💸 Payments", value="`$setupi`, `$upi`, `$setltc`, `$ltc`, `$checkbalance`", inline=False)
    embed.add_field(name="🔨 Moderation", value="`$purge`, `$kick`, `$ban`", inline=False)
    embed.add_field(name="⚙️ Utility", value="`$ping`, `$help`", inline=False)
    embed.set_footer(text="All commands have 5s cooldown")
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help"))

bot.run(DISCORD_TOKEN)

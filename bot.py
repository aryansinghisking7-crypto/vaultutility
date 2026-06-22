import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
import qrcode
import io
import asyncio
from threading import Thread
from flask import Flask
import json

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Flask keep-alive for Render
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is alive!"
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
Thread(target=run_flask, daemon=True).start()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== STORAGE SYSTEM =====
DATA_FILE = "bot_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"upi": {}, "ltc": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_key(ctx_or_interaction):
    """Returns guild.id in servers, user.id in DMs"""
    guild = getattr(ctx_or_interaction, 'guild', None)
    if guild:
        return f"guild_{guild.id}"
    user = getattr(ctx_or_interaction, 'author', getattr(ctx_or_interaction, 'user', None))
    return f"user_{user.id}"

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print(f"Connected to {len(bot.guilds)} servers")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# ===== HELPER FOR HYBRID RESPONSES =====
async def send_response(ctx, content=None, embed=None, file=None, ephemeral=False):
    if isinstance(ctx, discord.Interaction):
        if ctx.response.is_done():
            await ctx.followup.send(content=content, embed=embed, file=file, ephemeral=ephemeral)
        else:
            await ctx.response.send_message(content=content, embed=embed, file=file, ephemeral=ephemeral)
    else:
        await ctx.send(content=content, embed=embed, file=file)

# ===== DM + SERVER COMMANDS =====

@bot.hybrid_command(name="ping", description="Check if bot is alive")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def ping(ctx):
    await send_response(ctx, f"🏓 Pong! {round(bot.latency * 1000)}ms")

@bot.hybrid_command(name="bolbro", description="Spam a message 10 times")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def bolbro(ctx, *, message: str):
    if isinstance(ctx, discord.Interaction):
        await ctx.response.defer(ephemeral=True)

    for _ in range(10):
        if isinstance(ctx, discord.Interaction):
            await ctx.channel.send(message)
        else:
            await ctx.send(message)
        await asyncio.sleep(0.5)

    await send_response(ctx, "✅ Done spamming", ephemeral=True)

@bot.hybrid_command(name="setupi", description="Set UPI ID for payments")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def setupi(ctx, upi_id: str):
    data = load_data()
    key = get_key(ctx)
    data["upi"][key] = upi_id
    save_data(data)

    location = "this server" if ctx.guild else "your DMs"
    await send_response(ctx, f"✅ UPI ID set to `{upi_id}` for {location}", ephemeral=True)

@bot.hybrid_command(name="upi", description="Generate UPI QR for payment")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def upi(ctx, amount: float, note: str = "Payment"):
    data = load_data()
    key = get_key(ctx)
    upi_id = data["upi"].get(key)

    if not upi_id:
        await send_response(ctx, "❌ UPI ID not set. Use `/setupi` first.", ephemeral=True)
        return

    upi_link = f"upi://pay?pa={upi_id}&pn=User&am={amount}&tn={note}&cu=INR"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=512x512&data={upi_link}"

    embed = discord.Embed(
        title="💸 UPI Payment Request",
        description=f"**Amount:** ₹{amount}\n**Note:** {note}\n**UPI ID:** `{upi_id}`",
        color=0x00FF00
    )
    embed.set_image(url=qr_url)
    embed.set_footer(text="Scan with any UPI app | Zyro Utility Bot")

    await send_response(ctx, embed=embed)

@bot.hybrid_command(name="setltc", description="Set your LTC wallet address")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def setltc(ctx, wallet: str):
    data = load_data()
    key = get_key(ctx)
    data["ltc"][key] = wallet
    save_data(data)

    location = "this server" if ctx.guild else "your DMs"
    await send_response(ctx, f"✅ LTC wallet set to `{wallet}` for {location}", ephemeral=True)

@bot.hybrid_command(name="ltc", description="Show LTC payment info + QR")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def ltc(ctx, amount: float):
    data = load_data()
    key = get_key(ctx)
    wallet = data["ltc"].get(key)

    if not wallet:
        await send_response(ctx, "❌ LTC wallet not set. Use `/setltc` first.", ephemeral=True)
        return

    ltc_url = f"litecoin:{wallet}?amount={amount}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=512x512&data={ltc_url}"

    embed = discord.Embed(
        title="💰 LTC Payment Request",
        description=f"**Amount:** {amount} LTC\n**Address:** `{wallet}`",
        color=0x345d9d
    )
    embed.set_image(url=qr_url)
    embed.set_footer(text="Scan with any LTC wallet | Zyro Utility Bot")

    await send_response(ctx, embed=embed)

@bot.hybrid_command(name="checkbalance", description="Check saved UPI + LTC info")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def checkbalance(ctx):
    data = load_data()
    key = get_key(ctx)

    upi_id = data["upi"].get(key, "Not set")
    ltc_wallet = data["ltc"].get(key, "Not set")

    embed = discord.Embed(title="📊 Your Saved Info", color=0x7289da)
    embed.add_field(name="UPI ID", value=f"`{upi_id}`", inline=False)
    embed.add_field(name="LTC Wallet", value=f"`{ltc_wallet}`", inline=False)
    embed.set_footer(text="Server data" if ctx.guild else "DM data - only you can see this")

    await send_response(ctx, embed=embed, ephemeral=True)

# ===== SERVER ONLY COMMANDS =====

@bot.hybrid_command(name="purge", description="Delete messages", guild_only=True)
@app_commands.checks.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    if amount < 1 or amount > 100:
        await send_response(ctx, "❌ Amount must be 1-100", ephemeral=True)
        return

    if isinstance(ctx, discord.Interaction):
        await ctx.response.defer(ephemeral=True)
        await ctx.channel.purge(limit=amount)
        await ctx.followup.send(f"✅ Deleted {amount} messages", ephemeral=True)
    else:
        await ctx.channel.purge(limit=amount)
        await ctx.send(f"✅ Deleted {amount} messages", delete_after=3)

@bot.hybrid_command(name="sui", description="NUKE THE SERVER", guild_only=True)
@app_commands.checks.has_permissions(administrator=True)
async def sui(ctx):
    await send_response(ctx, "Nuke command disabled. Remove this line to re-enable.", ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)

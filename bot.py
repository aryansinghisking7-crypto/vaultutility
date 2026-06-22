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

# Global UPI storage
upi_storage = {}

def get_upi_id():
    return upi_storage.get("upi_id")

def set_upi_id(upi_id):
    upi_storage["upi_id"] = upi_id

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

# ===== DM + SERVER COMMANDS =====

@bot.hybrid_command(name="ping", description="Check if bot is alive")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def ping(ctx):
    await ctx.send("🏓 Pong! Bot is alive.")

@bot.hybrid_command(name="bolbro", description="Spam a message 10 times")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def bolbro(ctx, *, message: str):
    await ctx.defer(ephemeral=True)
    for _ in range(10):
        await ctx.send(message)
        await asyncio.sleep(0.5)
    await ctx.followup.send("✅ Done spamming", ephemeral=True)

@bot.hybrid_command(name="upi", description="Generate UPI QR for payment")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def upi(ctx, amount: float, note: str = "Payment"):
    upi_id = get_upi_id()
    if not upi_id:
        msg = "❌ UPI ID not set. Admin use `/setupi` in a server first."
        if isinstance(ctx, discord.Interaction):
            await ctx.response.send_message(msg, ephemeral=True)
        else:
            await ctx.send(msg)
        return

    upi_link = f"upi://pay?pa={upi_id}&pn=Zyro&am={amount}&tn={note}&cu=INR"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=512x512&data={upi_link}"

    embed = discord.Embed(title="💸 UPI Payment Request", description=f"**Amount:** ₹{amount}\n**Note:** {note}\n**UPI ID:** `{upi_id}`", color=0x00FF00)
    embed.set_image(url=qr_url)
    embed.set_footer(text="Scan with any UPI app | Zyro Utility Bot")
    
    if isinstance(ctx, discord.Interaction):
        await ctx.response.send_message(embed=embed)
    else:
        await ctx.send(embed=embed)

# ===== SERVER ONLY COMMANDS =====

@bot.hybrid_command(name="setupi", description="Set UPI ID for payments", guild_only=True)
@app_commands.checks.has_permissions(administrator=True)
async def setupi(ctx, upi_id: str):
    set_upi_id(upi_id)
    msg = f"✅ UPI ID set to: `{upi_id}`"
    if isinstance(ctx, discord.Interaction):
        await ctx.response.send_message(msg, ephemeral=True)
    else:
        await ctx.send(msg)

@bot.hybrid_command(name="purge", description="Delete messages", guild_only=True)
@app_commands.checks.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    if amount < 1 or amount > 100:
        msg = "❌ Amount must be 1-100"
        if isinstance(ctx, discord.Interaction):
            await ctx.response.send_message(msg, ephemeral=True)
        else:
            await ctx.send(msg)
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
    msg = "Nuke command disabled. Remove this line to re-enable."
    if isinstance(ctx, discord.Interaction):
        await ctx.response.send_message(msg, ephemeral=True)
    else:
        await ctx.send(msg)

if __name__ == "__main__":
    bot.run(TOKEN)

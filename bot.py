import discord
from discord.ext import commands
from discord import app_commands
import qrcode, io, requests, os
from flask import Flask
from threading import Thread

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Needed for kick/ban
bot = commands.Bot(command_prefix='$', intents=intents)

# --- Keep alive for Render ---
app = Flask('')
@app.route('/')
def home(): return "Zyro is alive!"
def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()
# -----------------------------

# --- Storage ---
user_data = {}  # {user_id: {"upi": "xxx@bank", "ltc": "address"}}

# --- Helper Functions ---
def get_upi(user_id):
    return user_data.get(user_id, {}).get("upi")

def get_ltc(user_id):
    return user_data.get(user_id, {}).get("ltc")

async def send_qr(interaction_or_ctx, data, title, filename):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    file = discord.File(buffer, filename=filename)
    embed = discord.Embed(title=title, color=0x00ff00)
    embed.set_image(url=f"attachment://{filename}")
    
    if isinstance(interaction_or_ctx, discord.Interaction):
        await interaction_or_ctx.response.send_message(embed=embed, file=file)
    else:
        await interaction_or_ctx.send(embed=embed, file=file)

# --- Events ---
@bot.event
async def on_ready():
    print(f'Zyro Bot is running! Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} slash commands')
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# --- UPI Commands ---
@bot.hybrid_command(name="setupi", description="Set your UPI ID")
@app_commands.describe(upi_id="Your UPI ID like name@bank")
async def setupi(ctx, upi_id: str):
    user_id = ctx.author.id if isinstance(ctx, commands.Context) else ctx.user.id
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["upi"] = upi_id
    
    msg = f"UPI ID set to `{upi_id}` ✅"
    if isinstance(ctx, commands.Context):
        await ctx.send(msg)
    else:
        await ctx.response.send_message(msg, ephemeral=True)

@bot.hybrid_command(name="upi", description="Generate UPI QR for payment")
@app_commands.describe(amount="Amount in INR", note="Payment note/reason")
async def upi(ctx, amount: float, *, note: str = "Payment"):
    user_id = ctx.author.id if isinstance(ctx, commands.Context) else ctx.user.id
    upi_id = get_upi(user_id)
    
    if not upi_id:
        msg = "You haven't set your UPI ID yet! Use `/setupi` or `$setupi yourupi@bank`"
        if isinstance(ctx, commands.Context):
            await ctx.send(msg)
        else:
            await ctx.response.send_message(msg, ephemeral=True)
        return
    
    upi_string = f"upi://pay?pa={upi_id}&pn=User&am={amount}&tn={note}"
    await send_qr(ctx, upi_string, f"UPI Payment - ₹{amount}", "upi_qr.png")

# --- LTC Commands ---
@bot.hybrid_command(name="setltc", description="Set your LTC wallet address")
@app_commands.describe(address="Your LTC wallet address")
async def setltc(ctx, address: str):
    user_id = ctx.author.id if isinstance(ctx, commands.Context) else ctx.user.id
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["ltc"] = address
    
    msg = f"LTC address set ✅"
    if isinstance(ctx, commands.Context):
        await ctx.send(msg)
    else:
        await ctx.response.send_message(msg, ephemeral=True)

@bot.hybrid_command(name="ltc", description="Generate LTC QR for payment")
@app_commands.describe(amount="Amount in LTC", note="Payment note")
async def ltc(ctx, amount: float, *, note: str = "Payment"):
    user_id = ctx.author.id if isinstance(ctx, commands.Context) else ctx.user.id
    ltc_address = get_ltc(user_id)
    
    if not ltc_address:
        msg = "You haven't set your LTC address yet! Use `/setltc` or `$setltc address`"
        if isinstance(ctx, commands.Context):
            await ctx.send(msg)
        else:
            await ctx.response.send_message(msg, ephemeral=True)
        return
    
    ltc_string = f"litecoin:{ltc_address}?amount={amount}&message={note}"
    await send_qr(ctx, ltc_string, f"LTC Payment - {amount} LTC", "ltc_qr.png")

@bot.hybrid_command(name="checkbalance", description="Check LTC wallet balance")
async def checkbalance(ctx):
    user_id = ctx.author.id if isinstance(ctx, commands.Context) else ctx.user.id
    ltc_address = get_ltc(user_id)
    
    if not ltc_address:
        msg = "You haven't set your LTC address yet! Use `/setltc` or `$setltc address`"
        if isinstance(ctx, commands.Context):
            await ctx.send(msg)
        else:
            await ctx.response.send_message(msg, ephemeral=True)
        return
    
    try:
        response = requests.get(f"https://api.blockcypher.com/v1/ltc/main/addrs/{ltc_address}/balance", timeout=10)
        data = response.json()
        balance = data.get('balance', 0) / 100000000  # Convert from litoshis to LTC
        
        embed = discord.Embed(title="LTC Wallet Balance", color=0x345D9D)
        embed.add_field(name="Address", value=f"`{ltc_address}`", inline=False)
        embed.add_field(name="Balance", value=f"`{balance:.8f} LTC`", inline=False)
        
        if isinstance(ctx, commands.Context):
            await ctx.send(embed=embed)
        else:
            await ctx.response.send_message(embed=embed)
    except Exception as e:
        msg = f"Error fetching balance: {str(e)}"
        if isinstance(ctx, commands.Context):
            await ctx.send(msg)
        else:
            await ctx.response.send_message(msg, ephemeral=True)

# --- Utility Commands ---
@bot.hybrid_command(name="ping", description="Check bot latency")
async def ping(ctx):
    latency = round(bot.latency * 1000)
    msg = f"Pong! 🏓 `{latency}ms`"
    if isinstance(ctx, commands.Context):
        await ctx.send(msg)
    else:
        await ctx.response.send_message(msg)

@bot.hybrid_command(name="help", description="Show all commands")
async def help_cmd

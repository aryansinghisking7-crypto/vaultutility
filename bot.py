import discord
from discord.ext import commands
from discord import app_commands
import qrcode, io, requests, os
from flask import Flask
from threading import Thread

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='$', intents=intents)

# --- Keep alive for Render ---
app = Flask('')
@app.route('/')
def home(): return "Zyro is alive!"
def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()
# -----------------------------

# --- Storage ---
user_data = {}

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
        balance = data.get('balance', 0) / 100000000
        
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
async def help_cmd(ctx):
    embed = discord.Embed(title="Zyro Bot Commands", color=0x00ff00)
    embed.add_field(name="💸 Payment", value="`/upi <amount> ` - Generate UPI QR\n`/setupi <upi_id>` - Set UPI ID\n`/ltc <amount> ` - Generate LTC QR\n`/setltc <address>` - Set LTC address\n`/checkbalance` - Check LTC balance", inline=False)
    embed.add_field(name="🛠️ Moderation", value="`/kick <user> [reason]` - Kick user\n`/ban <user> [reason]` - Ban user\n`/purge <amount>` - Delete messages", inline=False)
    embed.add_field(name="⚙️ Utility", value="`/ping` - Check latency\n`/help` - Show this menu", inline=False)
    embed.set_footer(text="Works with $ prefix too! Example: $upi 100")
    
    if isinstance(ctx, commands.Context):
        await ctx.send(embed=embed)
    else:
        await ctx.response.send_message(embed=embed)

# --- Moderation Commands [Guild Only] ---
@bot.hybrid_command(name="kick", description="Kick a user from the server")
@app_commands.describe(user="User to kick", reason="Reason for kick")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(ctx, user: discord.Member, *, reason: str = "No reason provided"):
    if isinstance(ctx, discord.Interaction):
        if not ctx.guild:
            await ctx.response.send_message("This command only works in servers!", ephemeral=True)
            return
        await user.kick(reason=reason)
        await ctx.response.send_message(f"Kicked {user.mention} | Reason: {reason}")
    else:
        if not ctx.guild:
            await ctx.send("This command only works in servers!")
            return
        await user.kick(reason=reason)
        await ctx.send(f"Kicked {user.mention} | Reason: {reason}")

@kick.error
async def kick_error(ctx, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        msg = "You don't have permission to kick members!"
    else:
        msg = f"Error: {str(error)}"
    
    if isinstance(ctx, discord.Interaction):
        await ctx.response.send_message(msg, ephemeral=True)
    else:
        await ctx.send(msg)

@bot.hybrid_command(name="ban", description="Ban a user from the server")
@app_commands.describe(user="User to ban", reason="Reason for ban")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(ctx, user: discord.Member, *, reason: str = "No reason provided"):
    if isinstance(ctx, discord.Interaction):
        if not ctx.guild:
            await ctx.response.send_message("This command only works in servers!", ephemeral=True)
            return
        await user.ban(reason=reason)
        await ctx.response.send_message(f"Banned {user.mention} | Reason: {reason}")
    else:
        if not ctx.guild:
            await ctx.send("This command only works in servers!")
            return
        await user.ban(reason=reason)
        await ctx.send(f"Banned {user.mention} | Reason: {reason}")

@ban.error
async def ban_error(ctx, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        msg = "You don't have permission to ban members!"
    else:
        msg = f"Error: {str(error)}"
    
    if isinstance(ctx, discord.Interaction):
        await ctx.response.send_message(msg, ephemeral=True)
    else:
        await ctx.send(msg)

@bot.hybrid_command(name="purge", description="Delete messages")
@app_commands.describe(amount="Number of messages to delete (1-100)")
@app_commands.checks.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    if amount < 1 or amount > 100:
        msg = "Amount must be between 1 and 100!"
        if isinstance(ctx, discord.Interaction):
            await ctx.response.send_message(msg, ephemeral=True)
        else:
            await ctx.send(msg)
        return
    
    if isinstance(ctx, discord.Interaction):
        if not ctx.guild:
            await ctx.response.send_message("This command only works in servers!", ephemeral=True)
            return
        await ctx.response.defer(ephemeral=True)
        deleted = await ctx.channel.purge(limit=amount)
        await ctx.followup.send(f"Deleted {len(deleted)} messages ✅", ephemeral=True)
    else:
        if not ctx.guild:
            await ctx.send("This command only works in servers!")
            return
        deleted = await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f"Deleted {len(deleted)-1} messages ✅", delete_after=3)

@purge.error
async def purge_error(ctx, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        msg = "You don't have permission to manage messages!"
    else:
        msg = f"Error: {str(error)}"
    
    if isinstance(ctx, discord.Interaction):
        await ctx.response.send_message(msg, ephemeral=True)
    else:
        await ctx.send(msg)

# --- Run Bot ---
bot.run(os.getenv('DISCORD_TOKEN'))

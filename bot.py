import discord
from discord.ext import commands
from discord import app_commands
import qrcode, io, requests, os, asyncio
from flask import Flask
from threading import Thread

# --- Config ---
OWNER_ID = int(os.getenv('OWNER_ID', 0))
if OWNER_ID == 0:
    print("WARNING: OWNER_ID not set. /bolbro won't work in DMs")
# -----------------------------

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='$', intents=intents)
bot.remove_command('help')
# -----------------------------

# --- Keep alive for Render ---
app = Flask('')
@app.route('/')
def home(): return "Zyro is alive!"
def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()
# -----------------------------

# --- Storage ---
user_data = {}

# --- Events ---
@bot.event
async def on_ready():
    print(f'Zyro Bot is running! Logged in as {bot.user}')
    print(f'Bot ID: {bot.user.id}')
    print(f'OWNER_ID set to: {OWNER_ID}')
    try:
        print("Starting command sync...")
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} GLOBAL slash commands')
        for cmd in synced:
            print(f"Synced: {cmd.name}")
    except Exception as e:
        print(f"FAILED TO SYNC: {type(e).__name__}: {e}")

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
    embed.add_field(name="💸 Payment", value="`/upi <amount>` - Generate UPI QR\n`/setupi <upi_id>` - Set UPI ID\n`/ltc <amount>` - Generate LTC QR\n`/setltc <address>` - Set LTC address\n`/checkbalance` - Check LTC balance", inline=False)
    embed.add_field(name="🛠️ Moderation", value="`/kick <user> [reason]` - Kick user\n`/ban <user> [reason]` - Ban user\n`/purge <amount>` - Delete messages\n`/sui` - NUKE SERVER\n*Server only*", inline=False)
    embed.add_field(name="⚙️ Utility", value="`/ping` - Check latency\n`/help` - Show this menu\n`/bolbro <message>` - Spam message 10x", inline=False)
    embed.set_footer(text="Works with $ prefix too! Example: $upi 100")
    
    if isinstance(ctx, commands.Context):
        await ctx.send(embed=embed)
    else:
        await ctx.response.send_message(embed=embed)

# --- Spam Command ---
@bot.hybrid_command(name="bolbro", description="Spam a message 10 times")
@app_commands.describe(message="Message to spam")
async def bolbro(ctx, *, message: str):
    user = ctx.author if isinstance(ctx, commands.Context) else ctx.user
    
    if ctx.guild:
        if not user.guild_permissions.administrator:
            msg = "You need Administrator permission to use this!"
            if isinstance(ctx, discord.Interaction):
                await ctx.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
    else:
        if user.id != OWNER_ID or OWNER_ID == 0:
            msg = "You can't use this command in DMs!"
            if isinstance(ctx, discord.Interaction):
                await ctx.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
    
    if isinstance(ctx, discord.Interaction):
        await ctx.response.send_message("Spamming...", ephemeral=True)
        channel = ctx.channel
    else:
        await ctx.send("Spamming...")
        channel = ctx.channel
    
    for i in range(10):
        await channel.send(message)
        await asyncio.sleep(0.8)

# --- Moderation Commands [Guild Only] ---
@bot.hybrid_command(name="kick", description="Kick a user from the server", guild_only=True)
@app_commands.checks.has_permissions(kick_members=True)
@app_commands.describe(user="User to kick", reason="Reason for kick")
async def kick(ctx, user: discord.Member, *, reason: str = "No reason provided"):
    await user.kick(reason=reason)
    msg = f"Kicked {user.mention} | Reason: {reason}"
    if isinstance(ctx, discord.Interaction):
        await ctx.response.send_message(msg)
    else:
        await ctx.send(msg)

@kick.error
async def kick_error(ctx, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        msg = "You don't have permission to kick members!"
    elif isinstance(error, commands.NoPrivateMessage):
        msg = "This command only works in servers!"
    else:
        msg = f"Error: {str(error)}"
    
    if isinstance(ctx, discord.Interaction):
        if ctx.response.is_done():
            await ctx.followup.send(msg, ephemeral=True)
        else:
            await ctx.response.send_message(msg, ephemeral=True)
    else:
        await ctx.send(msg)

@bot.hybrid_command(name="ban", description="Ban a user from the server", guild_only=True)
@app_commands.checks.has_permissions(ban_members=True)
@app_commands.describe(user="User to ban", reason="Reason for ban")
async def ban(ctx, user: discord.Member, *, reason: str = "No reason provided"):
    await user.ban(reason=reason)
    msg = f"Banned {user.mention} | Reason: {reason}"
    if isinstance(ctx, discord.Interaction):
        await ctx.response.send_message(msg)
    else:
        await ctx.send(msg)

@ban.error
async def ban_error(ctx, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        msg = "You don't have permission to ban members!"
    elif isinstance(error, commands.NoPrivateMessage):
        msg = "This command only works in servers!"
    else:
        msg = f"Error: {str(error)}"
    
    if isinstance(ctx, discord.Interaction):
        if ctx.response.is_done():
            await ctx.followup.send(msg, ephemeral=True)
        else:
            await ctx.response.send_message(msg, ephemeral=True)
    else:
        await ctx.send(msg)

@bot.hybrid_command(name="purge", description="Delete messages", guild_only=True)
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(amount="Number of messages to delete (1-100)")
async def purge(ctx, amount: int):
    if amount < 1 or amount > 100:
        msg = "Amount must be between 1 and 100!"
        if isinstance(ctx, discord.Interaction):
            await ctx.response.send_message(msg, ephemeral=True)
        else:
            await ctx.send(msg)
        return
    
    if isinstance(ctx, discord.Interaction):
        await ctx.response.defer(ephemeral=True)
        deleted = await ctx.channel.purge(limit=amount)
        await ctx.followup.send(f"Deleted {len(deleted)} messages ✅", ephemeral=True)
    else:
        deleted = await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f"Deleted {len(deleted)-1} messages ✅", delete_after=3)

@purge.error
async def purge_error(ctx, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        msg = "You don't have permission to manage messages!"
    elif isinstance(error, commands.NoPrivateMessage):
        msg = "This command only works in servers!"
    else:
        msg = f"Error: {str(error)}"
    
    if isinstance(ctx, discord.Interaction):
        if ctx.response.is_done():
            await ctx.followup.send(msg, ephemeral=True)
        else:
            await ctx.response.send_message(msg, ephemeral=True)
    else:
        await ctx.send(msg)

# --- NUKE COMMAND ---
@bot.hybrid_command(name="sui", description="NUKE THE SERVER", guild_only=True)
@app_commands.checks.has_permissions(administrator=True)
async def sui(ctx):
    guild = ctx.guild
    author = ctx.author if isinstance(ctx, commands.Context) else ctx.user
    
    if isinstance(ctx, discord.Interaction):
        await ctx.response.send_message("Starting nuke... muhehehehe", ephemeral=True)
    else:
        await ctx.send("Starting nuke... muhehehehe")
    
    for member in guild.members:
        if member.id == guild.owner_id or member.id == bot.user.id or member.id == author.id:
            continue
        try:
            await member.ban(reason=f"Nuked by {author}")
            await asyncio.sleep(0.5)
        except:
            pass
    
    for channel in guild.channels:
        try:
            await channel.delete()
            await asyncio.sleep(0.5)
        except:
            pass
    
    for i in range(10):
        try:
            await guild.create_text_channel(name="muhehehehe")
            await asyncio.sleep(0.5)
        except:
            pass

@sui.error
async def sui_error(ctx, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        msg = "You need Administrator permission to use this!"
    elif isinstance(error, commands.NoPrivateMessage):
        msg = "This command only works in servers!"
    else:
        msg = f"Error: {str(error)}"
    
    if isinstance(ctx, discord.Interaction):
        if ctx.response.is_done():
            await ctx.followup.send(msg, ephemeral=True)
        else:
            await ctx.response.send_message(msg, ephemeral=True)
    else:
        await ctx.send(msg)

# --- Run Bot ---
print("About to start bot with token...")
bot.run(os.getenv('DISCORD_TOKEN'))

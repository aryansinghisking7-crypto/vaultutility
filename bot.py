import discord
import os
import qrcode
import io
import requests
import asyncio
import json
import time
from groq import Groq

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Load persistent data
try:
    with open('user_data.json', 'r') as f:
        user_data = json.load(f)
except FileNotFoundError:
    user_data = {}

cooldowns = {}
COOLDOWN_TIME = 10

def save_data():
    with open('user_data.json', 'w') as f:
        json.dump(user_data, f)

def check_cooldown(user_id, command):
    current_time = time.time()
    if user_id not in cooldowns:
        cooldowns[user_id] = {}

    last_used = cooldowns[user_id].get(command, 0)
    time_diff = current_time - last_used

    if time_diff < COOLDOWN_TIME:
        return COOLDOWN_TIME - time_diff

    cooldowns[user_id][command] = current_time
    return 0

@client.event
async def on_ready():
    print(f'Bot logged in as {client.user}')

@client.event
async def on_message(message

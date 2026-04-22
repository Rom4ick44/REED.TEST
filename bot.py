import discord
from dotenv import load_dotenv
load_dotenv()
from discord.ext import commands
import asyncio
import os
from config import TOKEN
import database as db

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.bans = True
intents.voice_states = True
intents.messages = True
intents.guild_messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

async def load_extensions():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and not filename.startswith('__'):
            await bot.load_extension(f'cogs.{filename[:-3]}')
            print(f'Загружен cog: {filename}')

@bot.event
async def on_ready():
    print(f'Бот {bot.user} запущен!')
    print('Команды:', [cmd.name for cmd in bot.commands])

async def main():
    # Инициализация БД до загрузки cogs
    await db.init_db()
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        # Закрытие пула при завершении
        if db._pool:
            asyncio.run(db.close_db())
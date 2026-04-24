import discord
from discord.ext import commands
import asyncio
import os
import database as db
import config
from config import TOKEN

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.bans = True
intents.voice_states = True
intents.messages = True
intents.guild_messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

EXCLUDED_COGS = {'admin_settings', 'payment', 'log_cog'}

async def load_enabled_extensions():
    """Загружает только разрешённые коги, пропуская уже загруженные."""
    for filename in os.listdir('./cogs'):
        if not filename.endswith('.py') or filename.startswith('__'):
            continue
        cog_name = filename[:-3]
        ext_name = f'cogs.{cog_name}'

        # Проверка на уже загруженное расширение (защита от дубликатов)
        if ext_name in bot.extensions:
            print(f'Расширение {ext_name} уже загружено, пропускаем.')
            continue

        # Служебные коги загружаем всегда
        if cog_name in EXCLUDED_COGS:
            await bot.load_extension(ext_name)
            print(f'Загружен служебный cog: {filename}')
            continue

        # Проверяем, включён ли ког
        key = f'cog_{cog_name}_enabled'
        enabled = str(db.get_setting(key, 'true')).lower()
        if enabled != 'true':
            print(f'Пропущен cog {filename} (отключён в настройках).')
            continue

        # Если оплата не прошла, пользовательские коги не грузятся
        payment_status = str(db.get_setting('PAYMENT_STATUS', 'unpaid')).lower()
        if payment_status != 'paid':
            print(f'Пропущен cog {filename} (неуплата).')
            continue

        await bot.load_extension(ext_name)
        print(f'Загружен cog: {filename}')

@bot.event
async def on_ready():
    print(f'Бот {bot.user} запущен!')
    print('Команды:', [cmd.name for cmd in bot.commands])

async def main():
    await db.init_db()
    await db.init_settings()
    await db.load_all_settings()

    for key, value in db.settings_cache.items():
        if hasattr(config, key):
            setattr(config, key, value)

    async with bot:
        await load_enabled_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        if db._pool:
            asyncio.run(db.close_db())
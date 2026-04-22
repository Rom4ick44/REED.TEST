import discord
from discord.ext import commands
import traceback
import sys
from datetime import datetime

# Импорт настроек из config.py
try:
    from config import (
        LOGGING_ENABLED, BOT_LOG_CHANNEL_ID, LOG_LEVELS
    )
except ImportError:
    LOGGING_ENABLED = True
    BOT_LOG_CHANNEL_ID = 0
    LOG_LEVELS = {
        'commands': True,
        'events': True,
        'errors': True,
        'ui': True,
        'voice': True,
        'messages': False,
        'debug': True,
        'role_changes': True,
        'http_errors': True,
    }

class LogCog(commands.Cog):
    """Логирует действия бота отдельными сообщениями."""

    def __init__(self, bot):
        self.bot = bot
        self.enabled = LOGGING_ENABLED and BOT_LOG_CHANNEL_ID != 0
        self.levels = LOG_LEVELS
        self.log_channel = None

        if self.enabled:
            self.bot.loop.create_task(self.init_log())

    async def init_log(self):
        await self.bot.wait_until_ready()
        self.log_channel = self.bot.get_channel(BOT_LOG_CHANNEL_ID)
        if not self.log_channel:
            print(f"⚠️ LogCog: Канал {BOT_LOG_CHANNEL_ID} не найден. Логирование отключено.")
            self.enabled = False
            return
        await self.add_log("🟢 **Бот запущен**", color=discord.Color.green())

    async def add_log(self, text: str, color: discord.Color = discord.Color.blue()):
        if not self.enabled or not self.log_channel:
            return

        # Формируем короткое сообщение без эмбеда или с небольшим эмбедом
        timestamp = datetime.now().strftime("%H:%M:%S")
        embed = discord.Embed(
            description=f"`[{timestamp}]` {text}",
            color=color
        )
        try:
            await self.log_channel.send(embed=embed)
        except discord.HTTPException as e:
            print(f"Ошибка при отправке лога: {e}")

    # ----- Слушатели событий -----
    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        if not self.enabled or not self.levels.get('commands', True):
            return
        await self.add_log(f"✅ **{ctx.author}** выполнил `{ctx.message.content}` в {ctx.channel.mention}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if not self.enabled or not self.levels.get('errors', True):
            return
        if isinstance(error, commands.CommandNotFound):
            return
        error_text = str(error)[:100]
        await self.add_log(f"❌ Ошибка команды у **{ctx.author}**: `{error_text}`", discord.Color.red())

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.enabled or not self.levels.get('events', True):
            return
        await self.add_log(f"🟢 Бот **{self.bot.user}** готов. Серверов: {len(self.bot.guilds)}", discord.Color.green())

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not self.enabled or not self.levels.get('events', True):
            return
        await self.add_log(f"👋 **{member}** зашёл на сервер **{member.guild.name}**", discord.Color.green())

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if not self.enabled or not self.levels.get('events', True):
            return
        await self.add_log(f"👋 **{member}** покинул сервер **{member.guild.name}**", discord.Color.red())

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if not self.enabled or not self.levels.get('role_changes', True):
            return
        if before.roles != after.roles:
            old_roles = set(before.roles)
            new_roles = set(after.roles)
            added = new_roles - old_roles
            removed = old_roles - new_roles
            for role in added:
                await self.add_log(f"➕ **{after}** получил роль {role.mention}", discord.Color.green())
            for role in removed:
                await self.add_log(f"➖ **{after}** лишился роли {role.mention}", discord.Color.red())

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not self.enabled or not self.levels.get('ui', True):
            return
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get('custom_id', 'неизвестно')
            values = interaction.data.get('values', [])
            value_info = f" (знач: {', '.join(values)})" if values else ""
            await self.add_log(f"🖱️ **{interaction.user}** нажал `{custom_id}`{value_info}", discord.Color.teal())
        elif interaction.type == discord.InteractionType.modal_submit:
            custom_id = interaction.data.get('custom_id', 'неизвестно')
            await self.add_log(f"📋 **{interaction.user}** отправил модалку `{custom_id}`", discord.Color.teal())
        elif interaction.type == discord.InteractionType.application_command:
            cmd = interaction.data.get('name', 'неизвестно')
            await self.add_log(f"🎛️ **{interaction.user}** использовал /{cmd}", discord.Color.teal())

    @commands.Cog.listener()
    async def on_error(self, event_method, *args, **kwargs):
        if not self.enabled or not self.levels.get('errors', True):
            return
        error_type, error, _ = sys.exc_info()
        await self.add_log(f"❗ Ошибка в `{event_method}`: `{error}`", discord.Color.dark_red())

async def setup(bot):
    await bot.add_cog(LogCog(bot))
    print("🎉 LogCog успешно загружен")
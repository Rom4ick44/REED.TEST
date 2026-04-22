import discord
from discord.ext import commands
from datetime import datetime, timedelta
import database as db
from config import LOGGING_CHANNEL_ID

class Logs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_channel_id = LOGGING_CHANNEL_ID
        print("✅ Cog Logs загружен")

    async def send_log(self, guild, embed):
        action_type = embed.title.split()[0] if embed.title else "unknown"
        user_id = None
        for field in embed.fields:
            if field.name == "Пользователь":
                import re
                match = re.search(r'<@!?(\d+)>', field.value)
                if match:
                    user_id = int(match.group(1))
                break
        await db.add_log(guild.id, user_id, action_type, embed.description or str(embed.to_dict()))

        channel = guild.get_channel(self.log_channel_id)
        if channel:
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        embed = discord.Embed(
            title="📥 Участник зашёл",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Пользователь", value=member.mention)
        embed.add_field(name="ID", value=member.id)
        embed.add_field(name="Аккаунт создан", value=discord.utils.format_dt(member.created_at, style='R'))
        await self.send_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        embed = discord.Embed(
            title="📤 Участник вышел",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Пользователь", value=member.mention)
        embed.add_field(name="ID", value=member.id)
        embed.add_field(name="Причина", value="Покинул сервер")
        await self.send_log(member.guild, embed)

    # Остальные слушатели аналогично: await self.send_log

    @commands.group(name="logs", invoke_without_command=True)
    async def logs_group(self, ctx):
        await ctx.send_help(ctx.command)

    @logs_group.command(name="search")
    async def search_logs(self, ctx, user: discord.Member = None, action: str = None, days: int = 7, limit: int = 20):
        # Парсинг аргументов можно оставить как есть
        args = ctx.message.content.split()[2:]
        user_id = user.id if user else None
        action_type = None
        start_date = None
        for arg in args:
            if arg.startswith("action:"):
                action_type = arg.split(":")[1]
            elif arg.startswith("days:"):
                days = int(arg.split(":")[1])
            elif arg.startswith("limit:"):
                limit = int(arg.split(":")[1])
        if days:
            start_date = (datetime.now() - timedelta(days=days)).isoformat()

        logs = await db.search_logs(ctx.guild.id, user_id, action_type, start_date, None, limit)
        if not logs:
            await ctx.send("📭 Логов не найдено.")
            return

        embed = discord.Embed(title="📜 Результаты поиска", color=discord.Color.blue())
        for log in logs:
            log_id, log_user_id, log_action, details, timestamp = log
            user = ctx.guild.get_member(log_user_id) or f"<@{log_user_id}>"
            dt = timestamp.strftime("%d.%m.%Y %H:%M:%S") if hasattr(timestamp, 'strftime') else str(timestamp)
            embed.add_field(
                name=f"{log_action} - {dt}",
                value=f"**Пользователь:** {user}\n**Детали:** {details[:200] if details else ''}",
                inline=False
            )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Logs(bot))
    print("🎉 Cog Logs успешно загружен")
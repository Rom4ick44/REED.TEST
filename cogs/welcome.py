import discord
from discord.ext import commands
from datetime import datetime, timezone
import database as db
from config import WELCOME_CHANNEL_ID, LOG_CHANNEL_ID, LEAVE_LOG_CHANNEL_ID, REQUEST_CHANNEL_ID, ROLE_GUEST

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ Cog Welcome инициализирован")

    def format_duration(self, seconds):
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        if days:
            return f"{days}д {hours}ч {minutes}м"
        elif hours:
            return f"{hours}ч {minutes}м"
        else:
            return f"{minutes}м"

    async def format_past_apps(self, guild, user_id):
        past_apps = await db.get_user_applications(user_id)
        if not past_apps:
            return "Нет"
        lines = []
        for app_id, status, date, msg_id in past_apps[:5]:
            # Приводим дату к строке, если это datetime
            date_str = date if isinstance(date, str) else date.isoformat()[:10]
            if msg_id:
                jump_url = f"https://discord.com/channels/{guild.id}/{REQUEST_CHANNEL_ID}/{msg_id}"
                lines.append(f"[#{app_id} - {status}]({jump_url}) ({date_str})")
            else:
                lines.append(f"#{app_id} - {status} ({date_str})")
        return "\n".join(lines)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        print(f"👤 Событие on_member_join для {member}")
        welcome_channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
        log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
        if not welcome_channel or not log_channel:
            print("❌ Каналы не найдены, проверьте ID")
            return

        guild = member.guild
        request_link = f"https://discord.com/channels/{guild.id}/{REQUEST_CHANNEL_ID}"

        guest_role = guild.get_role(ROLE_GUEST)
        if guest_role:
            await member.add_roles(guest_role, reason="Новый участник")
        else:
            print("❌ Роль гостя не найдена")

        await welcome_channel.send(f"||{member.mention}||")

        welcome_embed = discord.Embed(
            title=f"**{member.display_name}** присоединился к серверу!",
            description=f"Подать заявку в семью можно в канале: [Заявка]({request_link})",
            color=0x000000
        )
        banner_url = "https://cdn.discordapp.com/attachments/1476263725735346179/1476995652079845447/image.png?ex=69a326e4&is=69a1d564&hm=2de1512ce783425de92c134e30b5b60f7a4844802264f5b8d571793e81573691&"
        welcome_embed.set_image(url=banner_url)
        welcome_embed.set_footer(text=f"Всего участников: {guild.member_count}")
        await welcome_channel.send(embed=welcome_embed)

        log_embed = discord.Embed(
            title="🆕 Новый участник",
            description=f"Пользователь {member.mention} присоединился к серверу.",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        log_embed.set_thumbnail(url=member.display_avatar.url)
        log_embed.add_field(name="Имя", value=str(member), inline=True)
        log_embed.add_field(name="ID", value=member.id, inline=True)
        log_embed.add_field(
            name="Аккаунт создан",
            value=discord.utils.format_dt(member.created_at, style='F'),
            inline=True
        )
        log_embed.add_field(
            name="Присоединился к серверу",
            value=discord.utils.format_dt(member.joined_at, style='F'),
            inline=True
        )
        log_embed.set_footer(text=f"ID: {member.id}")
        await log_channel.send(embed=log_embed)
        print("✅ Приветствие отправлено")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        print(f"👤 Событие on_member_remove для {member}")
        leave_channel = self.bot.get_channel(LEAVE_LOG_CHANNEL_ID)
        if not leave_channel:
            print("❌ Канал для логов выхода не найден.")
            return
        try:
            if member.joined_at:
                now = datetime.now(timezone.utc)
                time_seconds = (now - member.joined_at).total_seconds()
                time_str = self.format_duration(int(time_seconds))
            else:
                time_str = "неизвестно"
            try:
                avatar_url = member.display_avatar.url
            except:
                avatar_url = member.default_avatar.url

            past_apps = await self.format_past_apps(member.guild, member.id)

            embed = discord.Embed(
                title="📤 Участник вышел",
                description=f"Пользователь {member.mention} покинул сервер.",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_thumbnail(url=avatar_url)
            embed.add_field(name="Имя", value=str(member), inline=True)
            embed.add_field(name="ID", value=member.id, inline=True)
            embed.add_field(
                name="Аккаунт создан",
                value=discord.utils.format_dt(member.created_at, style='F'),
                inline=True
            )
            embed.add_field(
                name="Был на сервере",
                value=time_str,
                inline=True
            )
            embed.add_field(
                name="Прошлые заявки",
                value=past_apps,
                inline=False
            )
            embed.set_footer(text=f"ID: {member.id}")
            await leave_channel.send(embed=embed)
            print(f"✅ Выход {member} залогирован в канале {leave_channel.name}")
        except Exception as e:
            print(f"❌ Ошибка при отправке лога выхода: {e}")
            import traceback
            traceback.print_exc()

    @commands.command()
    async def testjoin(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author
        await self.on_member_join(member)
        await ctx.send("✅ Тестовое приветствие отправлено (проверь каналы).", delete_after=5)

async def setup(bot):
    await bot.add_cog(Welcome(bot))
    print("🎉 Cog Welcome успешно загружен")
import discord
from discord.ext import commands, tasks
from discord import ui
from datetime import datetime, time, date, timedelta
import asyncio
import database as db
from config import INVITER_LEADERBOARD_CHANNEL_ID, INVITER_ROLE_ID, LEADER_ROLE_ID

PAY_PER_ACCEPT = 15000
WEEKLY_BONUS = 10000

# -------------------- Макет панели (Components V2, стабильная версия) --------------------
class InviterLayout(ui.LayoutView):
    def __init__(self, today_text, week_text, total_text):
        super().__init__()

        container = ui.Container(accent_color=0x2F3136, spoiler=False)

        # Заголовок
        container.add_item(ui.TextDisplay("## 📊 Панель инвайтеров"))

        # Разделитель и секция "Сегодня"
        container.add_item(ui.Separator())
        container.add_item(ui.TextDisplay(today_text))

        # Разделитель и секция "Неделя"
        container.add_item(ui.Separator())
        container.add_item(ui.TextDisplay(week_text))

        # Разделитель и секция "Всего"
        container.add_item(ui.Separator())
        container.add_item(ui.TextDisplay(total_text))

        self.add_item(container)

        # Кнопка для обновления (чтобы сообщение не считалось пустым)
        @ui.button(label="Обновить", style=discord.ButtonStyle.secondary, custom_id="inviter_refresh")
        async def refresh_btn(self, interaction: discord.Interaction, button: ui.Button):
            cog = interaction.client.get_cog('InviterSystem')
            if cog:
                await cog.update_leaderboard()
                await interaction.response.defer()
            else:
                await interaction.response.send_message("❌ Ошибка обновления.", ephemeral=True)

# -------------------- Основной ког --------------------
class InviterSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.leaderboard_channel_id = INVITER_LEADERBOARD_CHANNEL_ID
        self.daily_reset.start()
        self.weekly_reset.start()
        self.bot.loop.create_task(self.initialize_settings())

    async def initialize_settings(self):
        await self.bot.wait_until_ready()
        global PAY_PER_ACCEPT, WEEKLY_BONUS
        PAY_PER_ACCEPT = int(db.get_setting('INVITER_PAY_PER_ACCEPT', 15000))
        WEEKLY_BONUS = int(db.get_setting('INVITER_WEEKLY_BONUS', 10000))

    def cog_unload(self):
        self.daily_reset.cancel()
        self.weekly_reset.cancel()

    def get_guild(self):
        return self.bot.guilds[0] if self.bot.guilds else None

    def _get_member_name(self, uid):
        """Возвращает никнейм или упоминание."""
        guild = self.get_guild()
        if guild:
            member = guild.get_member(uid)
            if member:
                return member.display_name
        return f"<@{uid}>"

    # -------------------- Обновление панели --------------------
    async def update_leaderboard(self):
        channel = self.bot.get_channel(self.leaderboard_channel_id)
        if not channel:
            return

        daily = await db.get_inviter_leaderboard_daily()
        weekly = await db.get_inviter_leaderboard_weekly()
        total = await db.get_inviter_leaderboard_total()

        def format_section(rows, field, title):
            """Форматирует текст для секции."""
            lines = [f"### {title}"]
            if not rows:
                lines.append("Нет данных")
            else:
                for i, row in enumerate(rows, 1):
                    uid = row['user_id']
                    name = self._get_member_name(uid)
                    lines.append(f"{i}. {name} – {row[field]} обзв.")
            return "\n".join(lines)

        today_text = format_section(daily, "daily_calls", "Сегодня")
        week_text = format_section(weekly, "weekly_calls", "Неделя")
        total_text = format_section(total, "total_calls", "Всего")

        layout = InviterLayout(today_text, week_text, total_text)

        # Удаляем предыдущее сообщение бота (чтобы панель всегда была актуальной)
        try:
            async for msg in channel.history(limit=5):
                if msg.author == self.bot.user:
                    await msg.delete()
                    break
        except discord.HTTPException:
            pass

        # Отправляем новое сообщение с макетом
        await channel.send(view=layout)

    # -------------------- Выплаты лидерам --------------------
    async def send_daily_payments_to_leaders(self):
        guild = self.get_guild()
        if not guild:
            return
        leader_role = guild.get_role(LEADER_ROLE_ID)
        if not leader_role:
            return

        payments = await db.get_daily_payment_list()
        if not payments:
            return

        embed = discord.Embed(title="💰 Ежедневные выплаты инвайтерам", color=discord.Color.gold())
        total = 0
        desc = ""
        for uid, calls in payments:
            name = self._get_member_name(uid)
            amount = calls * PAY_PER_ACCEPT
            total += amount
            desc += f"{name}: {calls} обзвонов → {amount} 💵\n"
        embed.description = desc
        embed.set_footer(text=f"Общая сумма: {total} 💵")

        for member in leader_role.members:
            try:
                await member.send(embed=embed)
            except:
                pass

    # -------------------- Авто‑сбросы --------------------
    @tasks.loop(time=time(21, 0))
    async def daily_reset(self):
        await self.bot.wait_until_ready()
        today = date.today()
        await self.send_daily_payments_to_leaders()
        await db.reset_daily_stats()
        if today.weekday() == 6:
            await self.award_weekly_bonus()
            await db.reset_weekly_stats()
        await self.update_leaderboard()
        print("🔁 Ежедневный сброс и обновление панели инвайтеров.")

    @tasks.loop(time=time(21, 0))
    async def weekly_reset(self):
        if date.today().weekday() != 6:
            return
        await self.bot.wait_until_ready()
        await db.reset_weekly_stats()
        print("🔁 Недельный сброс статистики инвайтеров.")

    async def award_weekly_bonus(self):
        weekly = await db.get_inviter_leaderboard_weekly(limit=5)
        if not weekly:
            return
        max_calls = weekly[0]['weekly_calls']
        winners = [row for row in weekly if row['weekly_calls'] == max_calls]
        bonus_each = WEEKLY_BONUS // len(winners)
        for winner in winners:
            await db.add_inviter_payment(winner['user_id'], bonus_each, 'weekly_bonus')
        for winner in winners:
            user = self.bot.get_user(winner['user_id'])
            if user:
                try:
                    await user.send(f"🏆 Вы стали лидером недели по обзвонам! Вам начислен бонус: {bonus_each} 💵")
                except:
                    pass

    # -------------------- Команды --------------------
    @commands.command(name='inviter_stats')
    async def inviter_stats(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author
        stats = await db.get_inviter_stats(member.id)
        if not stats:
            return await ctx.send("📭 Статистика отсутствует.")
        embed = discord.Embed(title=f"Статистика обзвонов: {member.display_name}", color=0x2F3136)
        embed.add_field(name="Сегодня", value=f"Обзвонов: {stats['daily_calls']} | Принято: {stats['daily_accepted']}")
        embed.add_field(name="Неделя", value=f"Обзвонов: {stats['weekly_calls']}")
        embed.add_field(name="Всего", value=f"Обзвонов: {stats['total_calls']}")
        await ctx.send(embed=embed)

    @commands.command(name='setup_inviter_leaderboard')
    @commands.has_permissions(administrator=True)
    async def setup_inviter_leaderboard(self, ctx):
        self.leaderboard_channel_id = ctx.channel.id
        await db.set_setting('INVITER_LEADERBOARD_CHANNEL_ID', str(ctx.channel.id))
        await ctx.send("✅ Канал установлен.")
        await self.update_leaderboard()

    @commands.command(name='update_inviter_board')
    @commands.has_permissions(administrator=True)
    async def update_inviter_board(self, ctx):
        await self.update_leaderboard()
        await ctx.send("✅ Панель обновлена.")


async def setup(bot):
    if 'InviterSystem' not in bot.cogs:
        await bot.add_cog(InviterSystem(bot))
        print("🎉 Cog InviterSystem успешно загружен")
    else:
        print("⚠️ Cog InviterSystem уже загружен, пропуск")
import discord
from discord.ext import commands, tasks
from datetime import datetime, time, date, timedelta
from discord.ui import View, Button
import asyncio
import database as db
from config import INVITER_LEADERBOARD_CHANNEL_ID, INVITER_ROLE_ID

PAY_PER_ACCEPT = 15000
WEEKLY_BONUS = 10000

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

    async def update_leaderboard(self):
        channel = self.bot.get_channel(self.leaderboard_channel_id)
        if not channel:
            return

        daily = await db.get_inviter_leaderboard_daily()
        weekly = await db.get_inviter_leaderboard_weekly()
        total = await db.get_inviter_leaderboard_total()
        payments = await db.get_daily_payment_list()

        embed_daily = self.format_leaderboard_embed(daily, "📊 Топ обзвонов за сегодня", "daily_calls")
        embed_weekly = self.format_leaderboard_embed(weekly, "📅 Топ обзвонов за неделю", "weekly_calls")
        embed_total = self.format_leaderboard_embed(total, "🏆 Общий топ обзвонов", "total_calls")
        embed_pay = self.format_payment_embed(payments)

        messages = []
        async for msg in channel.history(limit=10):
            if msg.author == self.bot.user and msg.embeds:
                messages.append(msg)

        daily_msg = None
        weekly_msg = None
        total_msg = None
        pay_msg = None

        for msg in messages:
            title = msg.embeds[0].title
            if "Топ обзвонов за сегодня" in title:
                daily_msg = msg
            elif "Топ обзвонов за неделю" in title:
                weekly_msg = msg
            elif "Общий топ обзвонов" in title:
                total_msg = msg
            elif "Выплаты инвайтерам за сегодня" in title:
                pay_msg = msg

        if daily_msg:
            await daily_msg.edit(embed=embed_daily)
        else:
            await channel.send(embed=embed_daily)

        if weekly_msg:
            await weekly_msg.edit(embed=embed_weekly)
        else:
            await channel.send(embed=embed_weekly)

        if total_msg:
            await total_msg.edit(embed=embed_total)
        else:
            await channel.send(embed=embed_total)

        view = PaymentView(self.bot)
        if pay_msg:
            await pay_msg.edit(embed=embed_pay, view=view)
        else:
            await channel.send(embed=embed_pay, view=view)

    def format_leaderboard_embed(self, rows, title, field):
        embed = discord.Embed(title=title, color=0x2F3136)
        if not rows:
            embed.description = "Нет данных"
            return embed
        guild = self.get_guild()
        for i, row in enumerate(rows, 1):
            user_id = row['user_id']
            name = f"<@{user_id}>"
            if guild:
                member = guild.get_member(user_id)
                if member:
                    name = member.display_name
            embed.add_field(name=f"{i}. {name}", value=f"Обзвонов: {row[field]}", inline=False)
        return embed

    def format_payment_embed(self, payments):
        embed = discord.Embed(title="💰 Выплаты инвайтерам за сегодня", color=discord.Color.gold())
        if not payments:
            embed.description = "Нет обзвонов"
            return embed
        total = 0
        desc = ""
        guild = self.get_guild()
        for uid, calls in payments:
            user_id = uid
            name = f"<@{user_id}>"
            if guild:
                member = guild.get_member(user_id)
                if member:
                    name = member.display_name
            amount = calls * PAY_PER_ACCEPT
            total += amount
            desc += f"{name}: {calls} обзвонов → {amount} 💵\n"
        embed.description = desc
        embed.set_footer(text=f"Общая сумма: {total} 💵")
        return embed

    @tasks.loop(time=time(21, 0))
    async def daily_reset(self):
        await self.bot.wait_until_ready()
        today = date.today()
        if today.weekday() == 6:
            await self.award_weekly_bonus()
        await db.reset_daily_stats()
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
        guild = self.get_guild()
        for winner in winners:
            user = self.bot.get_user(winner['user_id'])
            if user:
                try:
                    await user.send(f"🏆 Вы стали лидером недели по обзвонам! Вам начислен бонус: {bonus_each} 💵")
                except:
                    pass

    @commands.command(name='inviter_stats')
    async def inviter_stats(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author
        stats = await db.get_inviter_stats(member.id)
        if not stats:
            return await ctx.send("📭 У этого пользователя ещё нет статистики обзвонов.")
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
        await ctx.send("✅ Канал для панели инвайтеров установлен.")
        await self.update_leaderboard()

    @commands.command(name='update_inviter_board')
    @commands.has_permissions(administrator=True)
    async def update_inviter_board(self, ctx):
        await self.update_leaderboard()
        await ctx.send("✅ Панель обновлена.")


class PaymentView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="✅ Выплачено", style=discord.ButtonStyle.success, custom_id="inviter_pay_done")
    async def pay_done(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Недостаточно прав.", ephemeral=True)

        # Обнуляем дневные счётчики всех инвайтеров
        await db.reset_daily_stats()
        await db.mark_daily_payments_paid()

        # Обновляем панель
        cog = self.bot.get_cog('InviterSystem')
        if cog:
            await cog.update_leaderboard()

        await interaction.response.send_message("✅ Ежедневные выплаты обнулены.", ephemeral=True)


async def setup(bot):
    if 'InviterSystem' not in bot.cogs:
        await bot.add_cog(InviterSystem(bot))
        print("🎉 Cog InviterSystem успешно загружен")
    else:
        print("⚠️ Cog InviterSystem уже загружен, пропуск")
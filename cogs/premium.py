import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Select, Modal, TextInput
import asyncio
import re
import io
import aiohttp
from datetime import datetime, time
import database as db
from config import (
    PREMIUM_REQUEST_CHANNEL_ID,
    PREMIUM_REVIEW_CHANNEL_ID,
    PREMIUM_LOG_CHANNEL_ID,
    PREMIUM_REVIEWER_ROLE_ID,
    PREMIUM_PAYOUT_ROLE_ID
)

CONTRACT_TYPES = ["Коробки", "Банк", "Ценная партия", "Конспирация"]

def has_reviewer_role(user):
    return any(role.id == PREMIUM_REVIEWER_ROLE_ID for role in user.roles)


class PremiumRequestView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="📋 Подать заявку на премию", style=discord.ButtonStyle.primary, custom_id="premium_request_button")
    async def request_premium(self, interaction: discord.Interaction, button: Button):
        select = Select(
            placeholder="Выберите тип контракта",
            options=[discord.SelectOption(label=t) for t in CONTRACT_TYPES]
        )
        async def select_callback(interaction2: discord.Interaction):
            contract_type = select.values[0]
            await interaction2.response.send_message(
                f"✅ Вы выбрали **{contract_type}**. Пожалуйста, отправьте скриншот в этот канал (вложением или ссылкой).",
                ephemeral=True
            )
            def check(msg):
                return msg.author == interaction.user and msg.channel.id == PREMIUM_REQUEST_CHANNEL_ID and (msg.attachments or re.search(r'https?://\S+', msg.content))
            try:
                msg = await self.bot.wait_for('message', timeout=120.0, check=check)
                
                # Получаем байты изображения
                image_bytes = None
                filename = "screenshot.png"
                
                if msg.attachments:
                    # Вложение: читаем байты
                    attachment = msg.attachments[0]
                    image_bytes = await attachment.read()
                    filename = attachment.filename
                else:
                    # Ссылка: пробуем скачать
                    match = re.search(r'(https?://\S+)', msg.content)
                    if match:
                        url = match.group(1)
                        try:
                            async with aiohttp.ClientSession() as session:
                                async with session.get(url, timeout=10) as resp:
                                    if resp.status == 200:
                                        image_bytes = await resp.read()
                                        # Определяем расширение
                                        content_type = resp.headers.get('content-type', '')
                                        if 'png' in content_type:
                                            filename = 'screenshot.png'
                                        elif 'jpeg' in content_type or 'jpg' in content_type:
                                            filename = 'screenshot.jpg'
                                        elif 'gif' in content_type:
                                            filename = 'screenshot.gif'
                                        else:
                                            filename = 'screenshot.png'
                        except Exception as e:
                            print(f"Ошибка скачивания по URL: {e}")
                
                if not image_bytes:
                    await interaction.followup.send("❌ Не удалось получить изображение.", ephemeral=True)
                    return
                
                # Создаём файл для отправки
                file = discord.File(io.BytesIO(image_bytes), filename=filename)
                
                # Сохраняем в БД (можно хранить URL, но у нас нет прямого URL после пересылки файлом)
                # Поэтому сохраним заглушку или ID сообщения с файлом
                req_id = await db.add_premium_request(interaction.user.id, contract_type, "file_attached")
                
                review_channel = self.bot.get_channel(PREMIUM_REVIEW_CHANNEL_ID)
                if review_channel:
                    # Сначала отправляем файл
                    file_msg = await review_channel.send(file=file)
                    # Затем эмбед с кнопками, где ссылка ведёт на сообщение с файлом
                    embed = discord.Embed(
                        title=f"💰 Заявка на премию #{req_id}",
                        description=f"**Тип:** {contract_type}\n**От:** {interaction.user.mention}",
                        color=discord.Color.gold(),
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="📎 Скриншот", value=f"[Открыть в сообщении]({file_msg.jump_url})", inline=False)
                    embed.set_footer(text=f"ID: {interaction.user.id}")
                    view = ReviewButtons(req_id, self.bot, file_msg.id)  # передаём ID сообщения с файлом
                    await review_channel.send(embed=embed, view=view)
                
                # Удаляем исходное сообщение пользователя
                try:
                    await msg.delete()
                except:
                    pass
                
                await interaction.followup.send(f"✅ Заявка #{req_id} отправлена на рассмотрение.", ephemeral=True)
                
            except asyncio.TimeoutError:
                await interaction.followup.send("⏰ Время ожидания истекло. Попробуйте снова.", ephemeral=True)

        select.callback = select_callback
        view = View()
        view.add_item(select)
        await interaction.response.send_message("Выберите тип контракта:", view=view, ephemeral=True)


class ReviewButtons(View):
    def __init__(self, req_id, bot, file_message_id=None):
        super().__init__(timeout=None)
        self.req_id = req_id
        self.bot = bot
        self.file_message_id = file_message_id

    @discord.ui.button(label="✅ Принять", style=discord.ButtonStyle.success, custom_id="premium_accept")
    async def accept(self, interaction: discord.Interaction, button: Button):
        if not has_reviewer_role(interaction.user):
            return await interaction.response.send_message("❌ У вас нет прав.", ephemeral=True)
        modal = PremiumAmountModal(self.req_id, self.bot, self.file_message_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger, custom_id="premium_reject")
    async def reject(self, interaction: discord.Interaction, button: Button):
        if not has_reviewer_role(interaction.user):
            return await interaction.response.send_message("❌ У вас нет прав.", ephemeral=True)
        req = await db.get_premium_request(self.req_id)
        if not req or req['status'] != 'pending':
            return await interaction.response.send_message("❌ Заявка уже обработана.", ephemeral=True)
        await db.update_premium_request_status(self.req_id, 'rejected', interaction.user.id)
        user = self.bot.get_user(req['user_id'])
        if user:
            try:
                await user.send(f"❌ Ваша заявка на премию #{self.req_id} отклонена.")
            except:
                pass
        await self.log_action(interaction.guild, req, 'rejected', interaction.user, amount=None)
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(name="Статус", value=f"❌ Отклонена {interaction.user.mention}", inline=False)
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("✅ Заявка отклонена.", ephemeral=True)

    async def log_action(self, guild, req, action, reviewer, amount=None):
        log_channel = guild.get_channel(PREMIUM_LOG_CHANNEL_ID)
        if not log_channel:
            return
        embed = discord.Embed(
            title=f"📋 Заявка #{req['id']} {action}",
            color=discord.Color.green() if action == 'approved' else discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Пользователь", value=f"<@{req['user_id']}>")
        embed.add_field(name="Тип", value=req['contract_type'])
        if amount:
            embed.add_field(name="Сумма", value=f"{amount} 💵")
        embed.add_field(name="Проверяющий", value=reviewer.mention)
        # Скриншот уже в отдельном сообщении, можно добавить ссылку на него
        if self.file_message_id:
            file_msg = await log_channel.guild.get_channel(PREMIUM_REVIEW_CHANNEL_ID).fetch_message(self.file_message_id)
            if file_msg:
                embed.add_field(name="Скриншот", value=f"[Открыть]({file_msg.jump_url})")
        await log_channel.send(embed=embed)


class PremiumAmountModal(Modal, title="Введите сумму премии"):
    def __init__(self, req_id, bot, file_message_id=None):
        super().__init__()
        self.req_id = req_id
        self.bot = bot
        self.file_message_id = file_message_id
        self.add_item(TextInput(label="Сумма", placeholder="например: 5000", required=True))

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.children[0].value)
        except ValueError:
            return await interaction.response.send_message("❌ Введите целое число.", ephemeral=True)
        if amount <= 0:
            return await interaction.response.send_message("❌ Сумма должна быть положительной.", ephemeral=True)

        req = await db.get_premium_request(self.req_id)
        if not req or req['status'] != 'pending':
            return await interaction.response.send_message("❌ Заявка уже обработана.", ephemeral=True)

        await db.update_premium_request_status(self.req_id, 'approved', interaction.user.id)
        await db.set_premium_amount(self.req_id, amount)

        user = self.bot.get_user(req['user_id'])
        if user:
            try:
                await user.send(f"✅ Ваша заявка на премию #{self.req_id} одобрена! Сумма: {amount} 💵")
            except:
                pass

        review_view = ReviewButtons(self.req_id, self.bot, self.file_message_id)
        await review_view.log_action(interaction.guild, req, 'approved', interaction.user, amount)

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(name="Статус", value=f"✅ Одобрена {interaction.user.mention}\nСумма: {amount} 💵", inline=False)
        await interaction.message.edit(embed=embed, view=None)

        await interaction.response.send_message(f"✅ Премия #{self.req_id} одобрена на сумму {amount}.", ephemeral=True)


class Premium(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(PremiumRequestView(self.bot))
        self.bot.loop.create_task(self.restore_review_views())
        self.daily_summary.start()

    def cog_unload(self):
        self.daily_summary.cancel()

    async def restore_review_views(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(PREMIUM_REVIEW_CHANNEL_ID)
        if not channel:
            return
        async for message in channel.history(limit=100):
            if message.author == self.bot.user and message.embeds and message.components:
                for embed in message.embeds:
                    if embed.title and embed.title.startswith("💰 Заявка на премию"):
                        view = ReviewButtons(0, self.bot)
                        await message.edit(view=view)

    @tasks.loop(time=time(21, 0))
    async def daily_summary(self):
        await self.bot.wait_until_ready()
        rows = await db.get_approved_unpaid_requests()
        if not rows:
            return
        user_totals = {}
        for user_id, amount in rows:
            user_totals[user_id] = user_totals.get(user_id, 0) + amount
        total = sum(user_totals.values())

        payout_channel = self.bot.get_channel(PREMIUM_REVIEW_CHANNEL_ID)
        if payout_channel:
            role = payout_channel.guild.get_role(PREMIUM_PAYOUT_ROLE_ID)
            content = f"{role.mention} Сводка премий за день" if role else "Сводка премий за день"
            embed = discord.Embed(
                title="💰 Ежедневная сводка премий",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            description = ""
            for uid, summ in user_totals.items():
                description += f"<@{uid}>: {summ} 💵\n"
            embed.description = description
            embed.add_field(name="Общая сумма", value=f"{total} 💵")
            await payout_channel.send(content=content, embed=embed)

        await db.mark_premiums_as_paid()

    @daily_summary.before_loop
    async def before_daily_summary(self):
        await self.bot.wait_until_ready()

    @commands.command(name="premium_summary")
    @commands.has_permissions(administrator=True)
    async def premium_summary_cmd(self, ctx):
        await self.daily_summary()
        await ctx.send("✅ Сводка отправлена.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup_premium_panel(self, ctx):
        channel = self.bot.get_channel(PREMIUM_REQUEST_CHANNEL_ID)
        if not channel:
            return await ctx.send("❌ Канал не найден. Проверьте PREMIUM_REQUEST_CHANNEL_ID.")
        embed = discord.Embed(
            title="📋 Подача заявки на премию",
            description="Нажмите кнопку ниже, чтобы подать заявку на премию за контракт.",
            color=0x2F3136
        )
        view = PremiumRequestView(self.bot)
        await channel.send(embed=embed, view=view)
        await ctx.send("✅ Панель установлена.")

    # Тестовые команды
    @commands.command(name='premium_test')
    @commands.has_permissions(administrator=True)
    async def premium_test(self, ctx, contract_type: str = None):
        if contract_type not in CONTRACT_TYPES:
            await ctx.send(f"❌ Укажите один из типов: {', '.join(CONTRACT_TYPES)}")
            return
        screenshot_url = "https://cdn.pixabay.com/photo/2015/04/23/22/00/tree-736885_1280.jpg"
        async with aiohttp.ClientSession() as session:
            async with session.get(screenshot_url) as resp:
                image_bytes = await resp.read()
        file = discord.File(io.BytesIO(image_bytes), filename="test_screenshot.jpg")
        req_id = await db.add_premium_request(ctx.author.id, contract_type, "file_attached")
        review_channel = self.bot.get_channel(PREMIUM_REVIEW_CHANNEL_ID)
        if review_channel:
            file_msg = await review_channel.send(file=file)
            embed = discord.Embed(
                title=f"💰 Заявка на премию #{req_id}",
                description=f"**Тип:** {contract_type}\n**От:** {ctx.author.mention}",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            embed.add_field(name="📎 Скриншот", value=f"[Открыть в сообщении]({file_msg.jump_url})", inline=False)
            embed.set_footer(text=f"ID: {ctx.author.id}")
            view = ReviewButtons(req_id, self.bot, file_msg.id)
            await review_channel.send(embed=embed, view=view)
        await ctx.send(f"✅ Тестовая заявка #{req_id} создана.")

    @commands.command(name='premium_pending')
    @commands.has_permissions(administrator=True)
    async def premium_pending(self, ctx):
        rows = await db.get_pending_premium_requests(limit=20)
        if not rows:
            return await ctx.send("📭 Нет ожидающих заявок.")
        embed = discord.Embed(title="⏳ Ожидающие заявки", color=discord.Color.orange())
        for req_id, user_id, ctype, url, _ in rows:
            embed.add_field(
                name=f"#{req_id} – {ctype}",
                value=f"<@{user_id}>",
                inline=False
            )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Premium(bot))
    print("🎉 Cog Premium успешно загружен")
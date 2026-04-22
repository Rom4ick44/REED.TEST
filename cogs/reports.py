import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
import json
import re
from datetime import datetime
import database as db
from config import (
    KICK_LOG_CHANNEL_ID,
    WEAPONS_LOG_CHANNEL_ID,
    EVENT_LOG_CHANNEL_ID,
    KICK_PANEL_CHANNEL_ID,
    WEAPONS_PANEL_CHANNEL_ID,
    EVENT_PANEL_CHANNEL_ID,
    REPORT_ACCESS_ROLES, ROLE_GUEST
)

def has_access(user):
    return any(role.id in REPORT_ACCESS_ROLES for role in user.roles)

async def send_log_to_channel(channel_id, guild, embed):
    channel = guild.get_channel(channel_id)
    if not channel:
        print(f"❌ Канал {channel_id} не найден")
        return False
    try:
        await channel.send(embed=embed)
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки в канал {channel_id}: {e}")
        return False

# ---------- Кики ----------
class StaticKickModal(Modal, title="Кик по статику"):
    def __init__(self):
        super().__init__()
        self.add_item(TextInput(label="Статик игрока", required=True, placeholder="например: Z6AXX"))
        self.add_item(TextInput(label="Причина", style=discord.TextStyle.paragraph, required=True))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        static = self.children[0].value.strip()
        reason = self.children[1].value.strip()
        guild = interaction.guild
        if not static:
            return await interaction.followup.send("❌ Статик не может быть пустым.", ephemeral=True)
        try:
            await db.add_kick(guild.id, interaction.user.id, None, reason, "static", static)
            kick_id = await db.get_last_kick_id(guild.id)
        except Exception as e:
            print(f"Ошибка БД: {e}")
            return await interaction.followup.send("❌ Ошибка базы данных.", ephemeral=True)
        embed = discord.Embed(title="📝 Кик по статику", color=discord.Color.red(), timestamp=datetime.now())
        embed.add_field(name="ID отчёта", value=f"#{kick_id}", inline=True)
        embed.add_field(name="Кто кикнул", value=interaction.user.mention, inline=True)
        embed.add_field(name="Статик", value=static, inline=True)
        embed.add_field(name="Причина", value=reason, inline=False)
        embed.set_footer(text=f"Создано: {interaction.user.display_name}")
        await send_log_to_channel(KICK_LOG_CHANNEL_ID, guild, embed)
        await interaction.followup.send("✅ Кик по статику залогирован.", ephemeral=True)

class ConfirmKickView(View):
    def __init__(self, guild, member, moderator, reason):
        super().__init__(timeout=60)
        self.guild = guild
        self.member = member
        self.moderator = moderator
        self.reason = reason

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if hasattr(self, 'message'):
            try:
                await self.message.edit(view=self)
            except:
                pass

    @discord.ui.button(label="✅ Продолжить", style=discord.ButtonStyle.success, custom_id="confirm_kick")
    async def confirm(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.moderator.id:
            return await interaction.response.send_message("❌ Только вызвавший может подтвердить.", ephemeral=True)
        await interaction.response.defer()
        try:
            await self.member.edit(roles=[self.guild.get_role(ROLE_GUEST)])
            await self.member.send(f"Вы кикнуты с {self.guild.name} по причине: {self.reason}")
        except:
            pass
        await db.add_kick(self.guild.id, self.moderator.id, self.member.id, self.reason, "discord")
        kick_id = await db.get_last_kick_id(self.guild.id)
        embed = discord.Embed(title="🔨 Кик участника", color=discord.Color.red(), timestamp=datetime.now())
        embed.add_field(name="ID отчёта", value=f"#{kick_id}", inline=True)
        embed.add_field(name="Кто кикнул", value=self.moderator.mention, inline=True)
        embed.add_field(name="Кикнутый", value=self.member.mention, inline=True)
        embed.add_field(name="Причина", value=self.reason, inline=False)
        embed.set_footer(text=f"Создано: {self.moderator.display_name}")
        await send_log_to_channel(KICK_LOG_CHANNEL_ID, self.guild, embed)
        confirm_embed = discord.Embed(title="✅ Кик подтверждён", description=f"{self.member.mention} кикнут.", color=discord.Color.green())
        await interaction.edit_original_response(embed=confirm_embed, view=None)
        await interaction.followup.send("✅ Кик выполнен.", ephemeral=True)

    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.danger, custom_id="cancel_kick")
    async def cancel(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.moderator.id:
            return await interaction.response.send_message("❌ Только вызвавший может отменить.", ephemeral=True)
        embed = discord.Embed(title="❌ Кик отменён", description="Действие отменено.", color=discord.Color.greyple())
        await interaction.response.edit_message(embed=embed, view=None)
        await interaction.followup.send("❌ Кик отменён.", ephemeral=True)

class KickUserModal(Modal, title="Кик участника"):
    def __init__(self):
        super().__init__()
        self.add_item(TextInput(label="ID или упоминание", placeholder="123456789 или @User", required=True))
        self.add_item(TextInput(label="Причина", style=discord.TextStyle.paragraph, required=True))

    async def on_submit(self, interaction: discord.Interaction):
        user_input = self.children[0].value.strip()
        reason = self.children[1].value
        user_id = None
        if user_input.isdigit():
            user_id = int(user_input)
        else:
            match = re.search(r'<@!?(\d+)>', user_input)
            if match:
                user_id = int(match.group(1))
        if not user_id:
            return await interaction.response.send_message("❌ Не распознано.", ephemeral=True)
        member = interaction.guild.get_member(user_id)
        if not member or member.bot or member == interaction.user:
            return await interaction.response.send_message("❌ Некорректный пользователь.", ephemeral=True)
        embed = discord.Embed(title="⚠️ Подтверждение кика", description=f"Кикнуть {member.mention}?", color=discord.Color.orange())
        embed.add_field(name="Причина", value=reason)
        embed.set_footer(text="60 секунд")
        view = ConfirmKickView(interaction.guild, member, interaction.user, reason)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        msg = await interaction.original_response()
        view.message = msg

class KickPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔨 Кик участника", style=discord.ButtonStyle.danger, custom_id="kick_user")
    async def kick_user(self, interaction: discord.Interaction, button: Button):
        if not has_access(interaction.user):
            return await interaction.response.send_message("❌ Нет прав.", ephemeral=True)
        await interaction.response.send_modal(KickUserModal())

    @discord.ui.button(label="📝 Кик по статику", style=discord.ButtonStyle.secondary, custom_id="kick_static")
    async def kick_static(self, interaction: discord.Interaction, button: Button):
        if not has_access(interaction.user):
            return await interaction.response.send_message("❌ Нет прав.", ephemeral=True)
        await interaction.response.send_modal(StaticKickModal())

# ---------- Оружие (без Пулик) ----------
class UpdateWeaponModal(Modal, title="Новое количество оружия"):
    def __init__(self, category):
        super().__init__()
        self.category = category
        self.add_item(TextInput(label="Новое количество", placeholder="Число", required=True))

    async def on_submit(self, interaction: discord.Interaction):
        try:
            new_amount = int(self.children[0].value)
        except ValueError:
            return await interaction.response.send_message("❌ Введите число.", ephemeral=True)
        if new_amount < 0:
            return await interaction.response.send_message("❌ Не может быть отрицательным.", ephemeral=True)

        guild = interaction.guild
        weapons = await db.get_current_weapons(guild.id)
        old_amount = weapons.get(self.category, 0)
        change = new_amount - old_amount

        await db.update_weapon_stock(guild.id, self.category, new_amount, change, f"Обновление до {new_amount}", interaction.user.id)

        embed = discord.Embed(title="🔫 Изменение склада", color=discord.Color.blue(), timestamp=datetime.now())
        embed.add_field(name="ID операции", value=f"#{await db.get_last_weapon_id(guild.id)}", inline=True)
        embed.add_field(name="Кто изменил", value=interaction.user.mention, inline=True)
        embed.add_field(name="Категория", value=self.category, inline=True)
        embed.add_field(name="Изменение", value=f"{'+' if change>0 else ''}{change}", inline=True)
        embed.add_field(name="Предыдущий остаток", value=str(old_amount), inline=True)
        embed.add_field(name="Новый остаток", value=str(new_amount), inline=True)
        embed.set_footer(text=f"Создано: {interaction.user.display_name}")

        await send_log_to_channel(WEAPONS_LOG_CHANNEL_ID, guild, embed)
        await update_weapons_panel_embed(guild)
        await interaction.response.send_message(f"✅ {self.category}: {old_amount} → {new_amount} ({'+' if change>0 else ''}{change})", ephemeral=True)

async def update_weapons_panel_embed(guild):
    channel = guild.get_channel(WEAPONS_PANEL_CHANNEL_ID)
    if not channel:
        return
    weapons = await db.get_current_weapons(guild.id)
    embed = discord.Embed(title="🔫 Текущий склад оружия", color=discord.Color.gold(), timestamp=datetime.now())
    if not weapons:
        embed.description = "Склад пуст"
    else:
        categories = ["Тяга", "Спешик", "Сайга"]
        for cat in categories:
            count = weapons.get(cat, 0)
            change = await db.get_last_weapon_change(guild.id, cat)
            if change > 0:
                change_text = f"(+{change})"
                emoji = "🟢"
            elif change < 0:
                change_text = f"({change})"
                emoji = "🔴"
            else:
                change_text = ""
                emoji = "⚪"
            embed.add_field(
                name=f"{emoji} {cat}",
                value=f"{count} {change_text}",
                inline=True
            )
    async for message in channel.history(limit=10):
        if message.author == guild.me and message.embeds and message.embeds[0].title == "🔫 Текущий склад оружия":
            await message.edit(embed=embed)
            return
    await channel.send(embed=embed)

class WeaponsPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔫 Изменить оружие", style=discord.ButtonStyle.primary, custom_id="weapon_update")
    async def weapon_update(self, interaction: discord.Interaction, button: Button):
        if not has_access(interaction.user):
            return await interaction.response.send_message("❌ Нет прав.", ephemeral=True)
        categories = ["Тяга", "Спешик", "Сайга"]
        select = discord.ui.Select(placeholder="Выберите категорию", options=[discord.SelectOption(label=cat) for cat in categories])
        async def select_callback(interaction2):
            modal = UpdateWeaponModal(select.values[0])
            await interaction2.response.send_modal(modal)
        select.callback = select_callback
        view = View()
        view.add_item(select)
        await interaction.response.send_message("Выберите категорию:", view=view, ephemeral=True)

    @discord.ui.button(label="📜 История склада", style=discord.ButtonStyle.secondary, custom_id="weapon_history")
    async def weapon_history(self, interaction: discord.Interaction, button: Button):
        if not has_access(interaction.user):
            return await interaction.response.send_message("❌ Нет прав.", ephemeral=True)
        history = await db.get_weapons_history(interaction.guild.id, limit=20)
        if not history:
            return await interaction.response.send_message("История пуста.", ephemeral=True)
        embed = discord.Embed(title="📜 История склада", color=discord.Color.blue())
        for date, category, remaining, change, comment, created_by in history:
            user = interaction.guild.get_member(created_by)
            user_name = user.mention if user else f"<@{created_by}>"
            sign = "+" if change > 0 else ""
            embed.add_field(
                name=f"{date} - {category}",
                value=f"**Изменение:** {sign}{change}\n**Остаток:** {remaining}\n**Кто:** {user_name}\n**Коммент:** {comment or '—'}",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ---------- Мероприятия ----------
class EventReportModal(Modal):
    def __init__(self, event_type, fields):
        super().__init__(title=f"Отчёт: {event_type}")
        self.event_type = event_type
        self.fields = fields
        for field in fields:
            self.add_item(TextInput(label=field, required=True))

    async def on_submit(self, interaction: discord.Interaction):
        data = {field: self.children[i].value for i, field in enumerate(self.fields)}
        guild = interaction.guild
        await db.add_event_report(guild.id, self.event_type, data, interaction.user.id)
        report_id = await db.get_last_event_report_id(guild.id)
        embed = discord.Embed(title=f"📋 Отчёт: {self.event_type}", color=discord.Color.purple(), timestamp=datetime.now())
        embed.add_field(name="ID отчёта", value=f"#{report_id}", inline=True)
        embed.add_field(name="Кто создал", value=interaction.user.mention, inline=True)
        for k, v in data.items():
            embed.add_field(name=k, value=v, inline=False)
        embed.set_footer(text=f"Создано: {interaction.user.display_name}")
        await send_log_to_channel(EVENT_LOG_CHANNEL_ID, guild, embed)
        await interaction.response.send_message("✅ Отчёт отправлен.", ephemeral=True)

class EventPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📋 Отчёт о мероприятии", style=discord.ButtonStyle.primary, custom_id="event_report")
    async def event_report(self, interaction: discord.Interaction, button: Button):
        if not has_access(interaction.user):
            return await interaction.response.send_message("❌ Нет прав.", ephemeral=True)
        event_types = {
            "Тайники": ["Время", "Что слутали?"],
            "Похитка": ["Время", "Сколько получили?"],
            "Контракты": ["Дата", "Какой контракт?"],
            "Остров": ["Дата", "Сколько были на острове?"]
        }
        options = [discord.SelectOption(label=name) for name in event_types.keys()]
        select = discord.ui.Select(placeholder="Выберите тип", options=options)
        async def select_callback(interaction2):
            event_type = select.values[0]
            fields = event_types[event_type]
            modal = EventReportModal(event_type, fields)
            await interaction2.response.send_modal(modal)
        select.callback = select_callback
        view = View()
        view.add_item(select)
        await interaction.response.send_message("Выберите тип мероприятия:", view=view, ephemeral=True)

# ---------- Cog ----------
class Reports(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(KickPanelView())
        self.bot.add_view(WeaponsPanelView())
        self.bot.add_view(EventPanelView())

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup_reports(self, ctx):
        kick_channel = self.bot.get_channel(KICK_PANEL_CHANNEL_ID)
        if kick_channel:
            embed = discord.Embed(title="👥 Управление киками", color=0x2F3136)
            await kick_channel.send(embed=embed, view=KickPanelView())
        else:
            await ctx.send(f"❌ Канал киков (ID {KICK_PANEL_CHANNEL_ID}) не найден.")

        weapons_channel = self.bot.get_channel(WEAPONS_PANEL_CHANNEL_ID)
        if weapons_channel:
            embed = discord.Embed(title="🔫 Текущий склад оружия", color=0x2F3136)
            await weapons_channel.send(embed=embed, view=WeaponsPanelView())
            await update_weapons_panel_embed(ctx.guild)
        else:
            await ctx.send(f"❌ Канал оружия (ID {WEAPONS_PANEL_CHANNEL_ID}) не найден.")

        event_channel = self.bot.get_channel(EVENT_PANEL_CHANNEL_ID)
        if event_channel:
            embed = discord.Embed(title="📅 Отчёты о мероприятиях", color=0x2F3136)
            await event_channel.send(embed=embed, view=EventPanelView())
        else:
            await ctx.send(f"❌ Канал мероприятий (ID {EVENT_PANEL_CHANNEL_ID}) не найден.")

        await ctx.send("✅ Панели управления установлены.")

async def setup(bot):
    await bot.add_cog(Reports(bot))
    print("🎉 Cog Reports успешно загружен")
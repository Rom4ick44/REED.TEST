import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
import asyncio
import re
import database as db
from config import (
    EVENTS_CREATION_CHANNEL_ID, EVENTS_CHANNEL_ID, EVENTS_LOG_CHANNEL_ID,
    EVENT_PRIVILEGED_ROLES, EVENT_ADMIN_ROLES, EVENT_VOICE_CHANNEL_ID
)

# ---------- Вспомогательные функции ----------
def has_event_admin(interaction, event_data):
    if interaction.user.id == event_data['creator_id']:
        return True
    user_roles = [r.id for r in interaction.user.roles]
    return any(role in user_roles for role in EVENT_ADMIN_ROLES)

async def send_log(guild, text):
    channel = guild.get_channel(EVENTS_LOG_CHANNEL_ID)
    if channel:
        await channel.send(text)

async def create_event_embed(event_data, event_id):
    """Создаёт embed с информацией и списками участников."""
    embed = discord.Embed(
        title=event_data['title'],
        color=0x2F3136
    )
    # Информация
    info = f"**Тип:** {event_data['type'].capitalize()}\n"
    if event_data.get('server'):
        info += f"**Сервер:** {event_data['server']}\n"
    if event_data.get('time'):
        info += f"**Время:** {event_data['time']}\n"
    info += f"**Лимит:** {event_data['limit']}\n"
    if event_data.get('group_name'):
        info += f"**Группа:** {event_data['group_name']}\n"
    info += f"**ID мероприятия:** {event_id}"
    embed.add_field(name="Информация об мероприятии", value=info, inline=False)

    # Основной состав
    main_count = await db.count_participants(event_id, 'main')
    main_list = await db.get_participants(event_id, 'main')
    main_list_str = "\n".join([f"<@{uid}>" for uid in main_list]) if main_list else "Никого"
    embed.add_field(
        name=f"Основной состав | {main_count}/{event_data['limit']}",
        value=main_list_str,
        inline=False
    )

    # Запасной состав
    sub_count = await db.count_participants(event_id, 'sub')
    sub_list = await db.get_participants(event_id, 'sub')
    sub_list_str = "\n".join([f"<@{uid}>" for uid in sub_list]) if sub_list else "Никого"
    embed.add_field(
        name=f"Запасной состав | {sub_count}",
        value=sub_list_str,
        inline=False
    )

    embed.set_footer(text=f"Создатель: {event_data['creator_id']}")
    return embed

async def update_event_message(event_id, event_data, guild):
    """Обновляет embed мероприятия."""
    channel = guild.get_channel(event_data['channel_id'])
    if not channel:
        return
    try:
        msg = await channel.fetch_message(event_data['message_id_info'])
        embed = await create_event_embed(event_data, event_id)
        await msg.edit(embed=embed)
    except Exception as e:
        print(f"Ошибка обновления сообщения: {e}")

# ---------- Модальные окна ----------
class CreateEventModal(Modal, title="Создание мероприятия"):
    def __init__(self, event_type):
        super().__init__()
        self.event_type = event_type
        self.add_item(TextInput(label="Название", required=True, max_length=100))
        self.add_item(TextInput(label="Лимит (целое число)", required=True, placeholder="35"))
        self.add_item(TextInput(label="Время", required=True, placeholder="16:16"))
        self.add_item(TextInput(label="Сервер", required=False, placeholder="Denver"))
        self.add_item(TextInput(label="Группа", required=False, placeholder="Z6AXX"))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            limit = int(self.children[1].value)
        except ValueError:
            return await interaction.followup.send("❌ Лимит должен быть числом.", ephemeral=True)

        title = self.children[0].value
        time = self.children[2].value
        server = self.children[3].value if len(self.children) > 3 else None
        group = self.children[4].value if len(self.children) > 4 else None

        event_channel = interaction.guild.get_channel(EVENTS_CHANNEL_ID)
        if not event_channel:
            return await interaction.followup.send("❌ Канал для мероприятий не настроен.", ephemeral=True)

        # Создаём embed
        embed = discord.Embed(
            title=title,
            color=0x2F3136
        )
        info = f"**Тип:** {self.event_type.capitalize()}\n"
        if server:
            info += f"**Сервер:** {server}\n"
        info += f"**Время:** {time}\n"
        info += f"**Лимит:** {limit}\n"
        if group:
            info += f"**Группа:** {group}\n"
        info += "**ID мероприятия:** Сохранение..."
        embed.add_field(name="Информация об мероприятии", value=info, inline=False)
        embed.add_field(name=f"Основной состав | 0/{limit}", value="Никого", inline=False)
        embed.add_field(name="Запасной состав | 0", value="Никого", inline=False)
        embed.set_footer(text=f"Создатель: {interaction.user.id}")

        msg = await event_channel.send(embed=embed)

        event_id = await db.add_event(
            msg.id, msg.id, msg.id,
            event_channel.id, interaction.user.id,
            self.event_type, title, server, time, None, limit, group
        )

        event_data = await db.get_event_by_message(msg.id)
        view = EventView(event_id, event_data, msg.id)
        await msg.edit(view=view)
        await update_event_message(event_id, event_data, interaction.guild)

        await interaction.followup.send(f"✅ Мероприятие создано! {msg.jump_url}", ephemeral=True)
        await send_log(interaction.guild, f"✅ Создано мероприятие **{title}** (ID {event_id}) пользователем {interaction.user.mention}")

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await interaction.followup.send("❌ Ошибка при создании.", ephemeral=True)
        print(error)

class EditEventModal(Modal, title="Редактирование мероприятия"):
    def __init__(self, event_data, message_id):
        super().__init__()
        self.event_data = event_data
        self.message_id = message_id
        self.add_item(TextInput(label="Название", default=event_data['title'], required=True, max_length=100))
        self.add_item(TextInput(label="Лимит", default=str(event_data['limit']), required=True))
        self.add_item(TextInput(label="Время", default=event_data['time'], required=True))
        self.add_item(TextInput(label="Сервер", default=event_data.get('server') or "", required=False))
        self.add_item(TextInput(label="Группа", default=event_data.get('group_name') or "", required=False))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            limit = int(self.children[1].value)
        except ValueError:
            return await interaction.followup.send("❌ Лимит должен быть числом.", ephemeral=True)

        updates = {
            'title': self.children[0].value,
            'limit': limit,
            'time': self.children[2].value,
            'server': self.children[3].value,
            'group_name': self.children[4].value,
        }
        await db.update_event(self.event_data['id'], **updates)

        new_event_data = await db.get_event_by_message(self.message_id)
        await update_event_message(self.event_data['id'], new_event_data, interaction.guild)
        await interaction.followup.send("✅ Мероприятие обновлено.", ephemeral=True)
        await send_log(interaction.guild, f"📝 Отредактировано мероприятие **{self.event_data['title']}** (ID {self.event_data['id']}) пользователем {interaction.user.mention}")

# ---------- Селект для административных действий ----------
class AdminSelect(Select):
    def __init__(self, event_id, event_data, message_id):
        self.event_id = event_id
        self.event_data = event_data
        self.message_id = message_id
        options = [
            discord.SelectOption(label="✏️ Редактировать информацию", value="edit"),
            discord.SelectOption(label="🔓 Открыть/закрыть", value="toggle_open"),
            discord.SelectOption(label="📋 Экспорт списков", value="export"),
            discord.SelectOption(label="🧹 Очистить списки", value="clear"),
            discord.SelectOption(label="🎤 Проверка по войсу", value="voice_check"),
            discord.SelectOption(label="✅ Завершить", value="finish"),
        ]
        super().__init__(placeholder="Административные действия...", min_values=1, max_values=1, options=options, custom_id=f"admin_select_{event_id}")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not has_event_admin(interaction, self.event_data):
            return await interaction.followup.send("❌ У вас нет прав на это действие.", ephemeral=True)

        action = self.values[0]

        if action == "edit":
            modal = EditEventModal(self.event_data, self.message_id)
            await interaction.response.send_modal(modal)
        elif action == "toggle_open":
            new_state = 0 if self.event_data['is_open'] else 1
            await db.update_event(self.event_id, is_open=new_state)
            self.event_data['is_open'] = new_state
            await update_event_message(self.event_id, self.event_data, interaction.guild)
            state_text = "открыта" if new_state else "закрыта"
            await interaction.followup.send(f"✅ Регистрация {state_text}.", ephemeral=True)
            await send_log(interaction.guild, f"🔓 Регистрация на мероприятие **{self.event_data['title']}** {state_text} пользователем {interaction.user.mention}")
        elif action == "export":
            main_ids = await db.get_participants(self.event_id, 'main')
            sub_ids = await db.get_participants(self.event_id, 'sub')
            main_text = ", ".join(str(uid) for uid in main_ids) if main_ids else "пусто"
            sub_text = ", ".join(str(uid) for uid in sub_ids) if sub_ids else "пусто"
            await interaction.followup.send(
                f"**Основной состав:**\n{main_text}\n\n**Запасной состав:**\n{sub_text}",
                ephemeral=True
            )
        elif action == "clear":
            await db.clear_participants(self.event_id)
            await update_event_message(self.event_id, self.event_data, interaction.guild)
            await interaction.followup.send("✅ Все списки очищены.", ephemeral=True)
        elif action == "voice_check":
            voice_channel = interaction.guild.get_channel(EVENT_VOICE_CHANNEL_ID)
            if not voice_channel:
                await interaction.followup.send("❌ Голосовой канал для проверки не настроен.", ephemeral=True)
                return
            main_participants = await db.get_participants(self.event_id, 'main')
            if not main_participants:
                await interaction.followup.send("В основном составе никого нет.", ephemeral=True)
                return
            members_in_voice = [m.id for m in voice_channel.members]
            missing = [uid for uid in main_participants if uid not in members_in_voice]
            if missing:
                missing_mentions = " ".join(f"<@{uid}>" for uid in missing)
                await interaction.followup.send(f"❌ Следующие участники отсутствуют в войсе:\n{missing_mentions}", ephemeral=True)
            else:
                await interaction.followup.send("✅ Все участники основного состава находятся в войс-канале.", ephemeral=True)
        elif action == "finish":
            await db.delete_event(self.event_id)
            channel = interaction.guild.get_channel(self.event_data['channel_id'])
            if channel:
                try:
                    msg = await channel.fetch_message(self.message_id)
                    embed = discord.Embed(
                        title=self.event_data['title'],
                        description="Мероприятие завершено.",
                        color=0x1E1F22
                    )
                    await msg.edit(embed=embed, view=None)
                except:
                    pass
            await interaction.followup.send("✅ Мероприятие завершено.", ephemeral=True)
            await send_log(interaction.guild, f"🏁 Завершено мероприятие **{self.event_data['title']}** (ID {self.event_id}) пользователем {interaction.user.mention}")

# ---------- Кнопка регистрации ----------
class RegisterButton(Button):
    def __init__(self, event_id, event_data, message_id):
        super().__init__(label="📝 Откинуть +", style=discord.ButtonStyle.primary, custom_id=f"register_{event_id}")
        self.event_id = event_id
        self.event_data = event_data
        self.message_id = message_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not self.event_data['is_open']:
            return await interaction.followup.send("❌ Регистрация на мероприятие закрыта.", ephemeral=True)

        user_id = interaction.user.id
        participants = await db.get_participants(self.event_id)
        if any(p[0] == user_id for p in participants):
            return await interaction.followup.send("❌ Вы уже записаны.", ephemeral=True)

        user_roles = [r.id for r in interaction.user.roles]
        is_privileged = any(role in user_roles for role in EVENT_PRIVILEGED_ROLES)

        if is_privileged:
            main_count = await db.count_participants(self.event_id, 'main')
            if main_count >= self.event_data['limit']:
                return await interaction.followup.send("❌ Основной состав уже заполнен.", ephemeral=True)
            await db.add_participant(self.event_id, user_id, 'main')
            await interaction.followup.send("✅ Вы записаны в основной состав!", ephemeral=True)
            await send_log(interaction.guild, f"📝 {interaction.user.mention} записался в основной состав мероприятия **{self.event_data['title']}**")
        else:
            await db.add_participant(self.event_id, user_id, 'sub')
            await interaction.followup.send("✅ Вы записаны в запасной состав!", ephemeral=True)
            await send_log(interaction.guild, f"📝 {interaction.user.mention} записался в запасной состав мероприятия **{self.event_data['title']}**")

        await update_event_message(self.event_id, self.event_data, interaction.guild)

# ---------- Кнопка удаления себя ----------
class UnregisterButton(Button):
    def __init__(self, event_id, event_data, message_id):
        super().__init__(label="❌ Убрать +", style=discord.ButtonStyle.danger, custom_id=f"unregister_{event_id}")
        self.event_id = event_id
        self.event_data = event_data
        self.message_id = message_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id
        participants = await db.get_participants(self.event_id)
        if not any(p[0] == user_id for p in participants):
            return await interaction.followup.send("❌ Вы не записаны на мероприятие.", ephemeral=True)

        await db.remove_participant(self.event_id, user_id)
        await interaction.followup.send("✅ Вы удалены из списков.", ephemeral=True)
        await send_log(interaction.guild, f"❌ {interaction.user.mention} удалился из мероприятия **{self.event_data['title']}**")

        await update_event_message(self.event_id, self.event_data, interaction.guild)

# ---------- Кнопки для перемещения ----------
class MoveToMainButton(Button):
    def __init__(self, event_id, event_data, message_id):
        super().__init__(label="⬆️ В основной состав", style=discord.ButtonStyle.secondary, custom_id=f"move_main_{event_id}")
        self.event_id = event_id
        self.event_data = event_data
        self.message_id = message_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not has_event_admin(interaction, self.event_data):
            return await interaction.followup.send("❌ У вас нет прав на это действие.", ephemeral=True)

        participants = await db.get_participants(self.event_id, 'sub')
        if not participants:
            return await interaction.followup.send("❌ В запасном составе никого нет.", ephemeral=True)

        options = []
        for uid in participants[:25]:
            user = interaction.guild.get_member(uid)
            name = user.display_name if user else str(uid)
            options.append(discord.SelectOption(label=name, value=str(uid)))

        select = discord.ui.Select(placeholder="Выберите участника для перемещения в основной состав", options=options)

        async def select_callback(interaction2):
            user_id = int(select.values[0])
            main_count = await db.count_participants(self.event_id, 'main')
            if main_count >= self.event_data['limit']:
                await interaction2.response.send_message("❌ Основной состав заполнен.", ephemeral=True)
                return
            await db.remove_participant(self.event_id, user_id)
            await db.add_participant(self.event_id, user_id, 'main')
            await update_event_message(self.event_id, self.event_data, interaction.guild)
            await interaction2.response.send_message(f"✅ Пользователь <@{user_id}> перемещён в основной состав.", ephemeral=True)
            await send_log(interaction.guild, f"🔄 Пользователь <@{user_id}> перемещён в основной состав мероприятия **{self.event_data['title']}** пользователем {interaction.user.mention}")

        select.callback = select_callback
        view = View()
        view.add_item(select)
        await interaction.followup.send("Выберите участника для перемещения:", view=view, ephemeral=True)

class MoveToSubButton(Button):
    def __init__(self, event_id, event_data, message_id):
        super().__init__(label="⬇️ В запасной состав", style=discord.ButtonStyle.secondary, custom_id=f"move_sub_{event_id}")
        self.event_id = event_id
        self.event_data = event_data
        self.message_id = message_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not has_event_admin(interaction, self.event_data):
            return await interaction.followup.send("❌ У вас нет прав на это действие.", ephemeral=True)

        participants = await db.get_participants(self.event_id, 'main')
        if not participants:
            return await interaction.followup.send("❌ В основном составе никого нет.", ephemeral=True)

        options = []
        for uid in participants[:25]:
            user = interaction.guild.get_member(uid)
            name = user.display_name if user else str(uid)
            options.append(discord.SelectOption(label=name, value=str(uid)))

        select = discord.ui.Select(placeholder="Выберите участника для перемещения в запасной состав", options=options)

        async def select_callback(interaction2):
            user_id = int(select.values[0])
            await db.remove_participant(self.event_id, user_id)
            await db.add_participant(self.event_id, user_id, 'sub')
            await update_event_message(self.event_id, self.event_data, interaction.guild)
            await interaction2.response.send_message(f"✅ Пользователь <@{user_id}> перемещён в запасной состав.", ephemeral=True)
            await send_log(interaction.guild, f"🔄 Пользователь <@{user_id}> перемещён в запасной состав мероприятия **{self.event_data['title']}** пользователем {interaction.user.mention}")

        select.callback = select_callback
        view = View()
        view.add_item(select)
        await interaction.followup.send("Выберите участника для перемещения:", view=view, ephemeral=True)

# ---------- Основной View мероприятия ----------
class EventView(View):
    def __init__(self, event_id, event_data, message_id):
        super().__init__(timeout=None)
        self.event_id = event_id
        self.event_data = event_data
        self.message_id = message_id
        self.add_item(RegisterButton(event_id, event_data, message_id))
        self.add_item(UnregisterButton(event_id, event_data, message_id))
        self.add_item(MoveToMainButton(event_id, event_data, message_id))
        self.add_item(MoveToSubButton(event_id, event_data, message_id))
        self.add_item(AdminSelect(event_id, event_data, message_id))

# ---------- Ког ----------
class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(PersistentCreateButtonView(self.bot))
        self.bot.loop.create_task(self.restore_events())

    async def restore_events(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(2)
        channel = self.bot.get_channel(EVENTS_CHANNEL_ID)
        if not channel:
            return
        async for message in channel.history(limit=200):
            if message.author == self.bot.user and message.embeds:
                event_data = await db.get_event_by_message(message.id)
                if event_data:
                    view = EventView(event_data['id'], event_data, message.id)
                    await message.edit(view=view)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup_events(self, ctx):
        channel = self.bot.get_channel(EVENTS_CREATION_CHANNEL_ID)
        if not channel:
            return await ctx.send("❌ Канал для создания мероприятий не найден.")
        embed = discord.Embed(
            title="📅 Создание мероприятия",
            description="Нажмите кнопку ниже, чтобы создать новое мероприятие.",
            color=0x2F3136
        )
        view = PersistentCreateButtonView(self.bot)
        await channel.send(embed=embed, view=view)
        await ctx.send("✅ Кнопка создания мероприятий установлена.")

class PersistentCreateButtonView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="📅 Создать мероприятие", style=discord.ButtonStyle.primary, custom_id="create_event_button")
    async def create_event(self, interaction: discord.Interaction, button: Button):
        options = [
            discord.SelectOption(label="Капт", value="capt"),
            discord.SelectOption(label="MCL/ВЗЗ/ВЗМ", value="mcl"),
            discord.SelectOption(label="Другие мероприятия", value="other")
        ]
        select = discord.ui.Select(placeholder="Выберите тип мероприятия", options=options)

        async def select_callback(interaction2):
            event_type = select.values[0]
            modal = CreateEventModal(event_type)
            await interaction2.response.send_modal(modal)

        select.callback = select_callback
        view = View()
        view.add_item(select)
        await interaction.response.send_message("Выберите тип мероприятия:", view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Events(bot))
    print("🎉 Cog Events успешно загружен")
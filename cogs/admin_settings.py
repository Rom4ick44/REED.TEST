import discord
from discord.ext import commands
from discord import ui
import database as db
import json
import os
from config import OWNER_USER_ID

def is_owner(ctx):
    return ctx.author.id == OWNER_USER_ID

class AdminSettings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- Настройки ----------
    @commands.group(name='settings', invoke_without_command=True)
    @commands.check(is_owner)
    async def settings_group(self, ctx):
        """Управление настройками бота (только владелец)."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @settings_group.command(name='reload')
    async def settings_reload(self, ctx):
        await db.load_all_settings()
        import config
        for key, value in db.settings_cache.items():
            if hasattr(config, key):
                setattr(config, key, value)
        await ctx.send("✅ Настройки перезагружены из БД.")

    @settings_group.command(name='set')
    async def settings_set(self, ctx, key: str, *, value: str):
        import config as cfg
        if key not in cfg.DEFAULT_SETTINGS:
            return await ctx.send(f"❌ Неизвестная настройка: {key}")
        try:
            default_val = cfg.DEFAULT_SETTINGS[key]
            if isinstance(default_val, bool):
                val = value.lower() in ('true', '1', 'yes')
            elif isinstance(default_val, int):
                val = int(value)
            elif isinstance(default_val, list):
                val = json.loads(value)
            else:
                val = value
            await db.set_setting(key, val)
            if hasattr(cfg, key):
                setattr(cfg, key, val)
            await ctx.send(f"✅ {key} = {val}")
        except Exception as e:
            await ctx.send(f"❌ Ошибка: {e}")

    @settings_group.command(name='reset')
    async def settings_reset(self, ctx, key: str):
        import config as cfg
        await db.reset_setting(key)
        if key in cfg.DEFAULT_SETTINGS:
            setattr(cfg, key, cfg.DEFAULT_SETTINGS[key])
        await ctx.send(f"✅ {key} сброшена на значение по умолчанию.")

    @settings_group.command(name='list')
    async def settings_list(self, ctx):
        import config as cfg
        embed = discord.Embed(title="Текущие настройки", color=0x2F3136)
        for key in sorted(cfg.DEFAULT_SETTINGS.keys()):
            value = getattr(cfg, key, 'не найдено')
            embed.add_field(name=key, value=str(value)[:1024], inline=False)
        await ctx.send(embed=embed)

    # ---------- Управление когами ----------
    @commands.group(name='cog', invoke_without_command=True)
    @commands.check(is_owner)
    async def cogs_group(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @cogs_group.command(name='disable')
    async def cogs_disable(self, ctx, cog_name: str):
        ext_name = f'cogs.{cog_name}'
        if ext_name in self.bot.extensions:
            await self.bot.unload_extension(ext_name)
        await db.set_setting(f'cog_{cog_name}_enabled', 'false')
        await ctx.send(f"🔒 Ког `{cog_name}` отключён.")

    @cogs_group.command(name='enable')
    async def cogs_enable(self, ctx, cog_name: str):
        if db.get_setting('PAYMENT_STATUS', 'unpaid') != 'paid':
            return await ctx.send("❌ Оплата не произведена. Сначала выполните `!payment_confirm`.")
        ext_name = f'cogs.{cog_name}'
        if ext_name not in self.bot.extensions:
            try:
                await self.bot.load_extension(ext_name)
            except Exception as e:
                return await ctx.send(f"❌ Ошибка загрузки: {e}")
        await db.set_setting(f'cog_{cog_name}_enabled', 'true')
        await ctx.send(f"✅ Ког `{cog_name}` включён.")

    @cogs_group.command(name='list')
    async def cogs_list(self, ctx):
        embed = discord.Embed(title="Статусы когов", color=0x2F3136)
        for filename in sorted(os.listdir('./cogs')):
            if filename.endswith('.py') and not filename.startswith('__'):
                cog_name = filename[:-3]
                enabled = db.get_setting(f'cog_{cog_name}_enabled', 'true')
                status = '✅' if enabled.lower() == 'true' else '❌'
                embed.add_field(name=cog_name, value=status, inline=True)
        await ctx.send(embed=embed)

    # ---------- Components V2 тест ----------
    @commands.command(name='testv2')
    @commands.check(is_owner)
    async def testv2_cmd(self, ctx):
        """Тест Components V2 — минимальный работающий пример."""
        # Определяем макет внутри метода
        class TestLayout(ui.LayoutView):
            # Текстовый блок
            header = ui.TextDisplay("## 🧪 Привет, V2!\nЭто самый простой макет.", id=1)

            # Кнопка
            @ui.button(label="Нажми", style=discord.ButtonStyle.primary, custom_id="testv2_btn")
            async def btn(self, interaction: discord.Interaction, button: ui.Button):
                await interaction.response.send_message("Кнопка работает!", ephemeral=True)

        await ctx.send(view=TestLayout())

async def setup(bot):
    await bot.add_cog(AdminSettings(bot))
    print("🎉 Cog AdminSettings успешно загружен")
import discord
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta
import database as db
from config import OWNER_USER_ID

EXCLUDED_COGS = {'admin_settings', 'payment', 'log_cog', 'logs'}

def is_owner(ctx):
    return ctx.author.id == OWNER_USER_ID

class Payment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_payment_status.start()
        self.bot.loop.create_task(self.startup_check())

    def cog_unload(self):
        self.check_payment_status.cancel()

    async def startup_check(self):
        await self.bot.wait_until_ready()
        status = db.get_setting('PAYMENT_STATUS', 'unpaid')
        if status == 'unpaid':
            await self.disable_all_except_excluded()
        expire_str = db.get_setting('PAYMENT_EXPIRE_DATE', '')
        if expire_str:
            try:
                expire_date = datetime.fromisoformat(expire_str)
                if datetime.now(timezone.utc) > expire_date:
                    await self.expire_payment()
            except:
                pass

    async def disable_all_except_excluded(self):
        """Выгружает все пользовательские коги и помечает их как отключённые в БД."""
        for ext_name in list(self.bot.extensions.keys()):
            cog_name = ext_name.replace('cogs.', '')
            if cog_name not in EXCLUDED_COGS:
                try:
                    await self.bot.unload_extension(ext_name)
                    # Ставим флаг false в БД, чтобы статус отображался правильно
                    await db.set_setting(f'cog_{cog_name}_enabled', 'false')
                    print(f"🔒 Ког {cog_name} выгружен (неуплата).")
                except Exception as e:
                    print(f"Ошибка выгрузки {cog_name}: {e}")

    async def enable_all_cogs(self):
        """Загружает все включённые в БД коги (возвращает им статус true)."""
        import os
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and not filename.startswith('__'):
                cog_name = filename[:-3]
                if cog_name in EXCLUDED_COGS:
                    continue
                key = f'cog_{cog_name}_enabled'
                # Включаем флаг в БД, чтобы при следующем старте ког загрузился
                await db.set_setting(key, 'true')
                ext_name = f'cogs.{cog_name}'
                if ext_name not in self.bot.extensions:
                    try:
                        await self.bot.load_extension(ext_name)
                        print(f"🔓 Ког {cog_name} загружен.")
                    except Exception as e:
                        print(f"Ошибка загрузки {cog_name}: {e}")

    async def expire_payment(self):
        await db.set_setting('PAYMENT_STATUS', 'unpaid')
        await self.disable_all_except_excluded()
        owner = self.bot.get_user(OWNER_USER_ID)
        if owner:
            try:
                await owner.send(
                    "⚠️ **Срок оплаты бота истёк**. Все коги, кроме служебных, отключены.\n"
                    "Для возобновления работы используйте команду `!payment_confirm <дней>`."
                )
            except:
                pass

    @tasks.loop(hours=1)
    async def check_payment_status(self):
        await self.bot.wait_until_ready()
        status = db.get_setting('PAYMENT_STATUS', 'unpaid')
        if status == 'paid':
            expire_str = db.get_setting('PAYMENT_EXPIRE_DATE', '')
            if expire_str:
                try:
                    expire_date = datetime.fromisoformat(expire_str)
                    if datetime.now(timezone.utc) > expire_date:
                        await self.expire_payment()
                except:
                    pass

    @check_payment_status.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    @commands.command(name='payment_confirm')
    @commands.check(is_owner)
    async def payment_confirm(self, ctx, days: int = 30):
        if days <= 0:
            return await ctx.send("❌ Количество дней должно быть положительным.")
        new_expire = datetime.now(timezone.utc) + timedelta(days=days)
        await db.set_setting('PAYMENT_STATUS', 'paid')
        await db.set_setting('PAYMENT_EXPIRE_DATE', new_expire.isoformat())
        await self.enable_all_cogs()
        await ctx.send(f"✅ Оплата подтверждена. Бот активен до {new_expire.strftime('%d.%m.%Y %H:%M')} UTC.")

    @commands.command(name='payment_revoke')
    @commands.check(is_owner)
    async def payment_revoke(self, ctx):
        await self.expire_payment()
        await ctx.send("🔒 Все коги отключены. Статус оплаты: unpaid.")

    @commands.command(name='payment_status')
    @commands.check(is_owner)
    async def payment_status(self, ctx):
        status = db.get_setting('PAYMENT_STATUS', 'unpaid')
        expire_str = db.get_setting('PAYMENT_EXPIRE_DATE', '')
        if expire_str:
            try:
                expire_date = datetime.fromisoformat(expire_str)
                expire_display = expire_date.strftime('%d.%m.%Y %H:%M UTC')
            except:
                expire_display = 'не задана'
        else:
            expire_display = 'не задана'
        await ctx.send(f"📊 Статус оплаты: **{status}**\nДата окончания: **{expire_display}**")

async def setup(bot):
    await bot.add_cog(Payment(bot))
    print("🎉 Cog Payment успешно загружен")
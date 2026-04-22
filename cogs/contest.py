import discord
from discord.ext import commands
import sqlite3  # уже не нужен, но оставим для совместимости? Нет, используем db
import database as db
from config import CONTEST_CHANNEL_ID, CONTEST_APPROVER_ROLE_ID, LEADERBOARD_CHANNEL_ID, EMOJI_FIRST_PLACE, EMOJI_SECOND_PLACE

class Contest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id != CONTEST_CHANNEL_ID:
            return
        if message.author.bot:
            return
        await db.add_invite_submission(message.author.id, message.id, message.channel.id)
        await message.add_reaction("✅")
        await message.add_reaction("❌")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return
        if payload.channel_id != CONTEST_CHANNEL_ID:
            return
        channel = self.bot.get_channel(payload.channel_id)
        try:
            message = await channel.fetch_message(payload.message_id)
        except:
            return
        if message.author.bot:
            return
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if not member:
            return
        if not any(role.id == CONTEST_APPROVER_ROLE_ID for role in member.roles):
            return
        if message.author.id == member.id:
            await message.remove_reaction(payload.emoji, member)
            return
        emoji = str(payload.emoji)
        invite_id = await db.get_invite_by_message(message.id)
        if not invite_id:
            return
        if emoji == "✅":
            await db.approve_invite(invite_id, member.id)
            await message.remove_reaction("✅", member)
            await message.remove_reaction("❌", member)
            try:
                await message.author.send(f"✅ Ваша заявка на конкурс принята! +1 балл.")
            except:
                pass
            await self.update_leaderboard(guild)
        elif emoji == "❌":
            await db.reject_invite(invite_id, member.id)
            await message.remove_reaction("✅", member)
            await message.remove_reaction("❌", member)
            try:
                await message.author.send(f"❌ Ваша заявка на конкурс отклонена.")
            except:
                pass

    async def update_leaderboard(self, guild):
        channel = guild.get_channel(LEADERBOARD_CHANNEL_ID)
        if not channel:
            return
        rows = await db.get_leaderboard()
        embed = discord.Embed(title="🏆 Рейтинг конкурса инвайтов", color=0x2F3136)
        if not rows:
            embed.description = "Пока нет участников."
        else:
            for i, (user_id, points) in enumerate(rows, 1):
                user = guild.get_member(user_id)
                name = user.display_name if user else f"<@{user_id}>"
                if i == 1:
                    medal = f"{EMOJI_FIRST_PLACE} "
                elif i == 2:
                    medal = f"{EMOJI_SECOND_PLACE} "
                else:
                    medal = f"{i}. "
                embed.add_field(name=f"{medal}{name}", value=f"Баллов: {points}", inline=False)
        async for msg in channel.history(limit=10):
            if msg.author == self.bot.user and msg.embeds:
                await msg.edit(embed=embed)
                return
        await channel.send(embed=embed)

    @commands.command(name="leaderboard")
    @commands.has_permissions(administrator=True)
    async def leaderboard_cmd(self, ctx):
        await self.update_leaderboard(ctx.guild)
        await ctx.send("✅ Таблица лидеров обновлена.", ephemeral=True)

    @commands.command(name="contest_reset")
    @commands.has_permissions(administrator=True)
    async def contest_reset(self, ctx):
        await db.reset_leaderboard()
        await self.update_leaderboard(ctx.guild)
        await ctx.send("✅ Рейтинг конкурса сброшен.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Contest(bot))
    print("🎉 Cog Contest успешно загружен")
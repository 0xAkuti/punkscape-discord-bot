from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from bot import PunkScapeBot


class Search(commands.Cog):
    def __init__(self, bot: PunkScapeBot):
        self.bot = bot

    @commands.command()
    async def date(self, ctx: commands.Context, date: str):
        try:
            target_date = datetime.datetime.fromisoformat(date)
        except ValueError:
            await ctx.send('Invalid date format. Write as the date as YYYY-MM-DD hh:mm. '
                           'Hour and minute are optional.')
            return
        closest_id = (abs(self.bot.nft_dates - target_date)).argmin() + 1
        await ctx.send(embed=await self.bot.create_punkscape_embed(closest_id))

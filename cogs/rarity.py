
from __future__ import annotations

from typing import TYPE_CHECKING

import discord
import requests
from discord.ext import commands
from ens import ENS
from web3 import Web3, WebsocketProvider

if TYPE_CHECKING:
    from bot import PunkScapeBot


class Rarity(commands.Cog):
    def __init__(self, bot: PunkScapeBot, endpoint_url: str):
        self.bot = bot
        self.w3 = Web3(WebsocketProvider(endpoint_url))
        self.ns = ENS.fromWeb3(self.w3)

    @commands.command()
    async def id(self, ctx: commands.Context, id: int):
        await ctx.send(embed=await self.bot.create_punkscape_embed(id))

    @commands.command()
    async def rank(self, ctx: commands.Context, rank: int):
        for id, ps in self.bot.nft_data.items():
            if ps['rank'] == rank-1:
                await ctx.send(embed=await self.bot.create_punkscape_embed(id))
                return
        else:
            await ctx.send('Invalid punkscape rank!')

    @commands.command()
    async def wallet(self, ctx: commands.Context, address: str):
        await ctx.trigger_typing()
        name = address
        if address.endswith('.eth'):
            address = self.ns.address(address)
        if not self.w3.isAddress(address):
            await ctx.send('Please provide a valid ethereum address or .eth name.')
            return
        elif name == address:
            address = self.w3.toChecksumAddress(address)
            name = self.ns.name(address)
            if not name:
                name = address
        scapes = requests.get(f'https://api.punkscape.xyz/address/{address}/punkscapes').json()
        ids = [ps['token_id'] for ps in scapes]
        ranks = [self.bot.nft_data[id]['rank']+1 for id in ids]
        data = sorted(zip(ranks, ids))
        embed = discord.Embed(title=f'PunkScapes of {name}')
        if len(ids) == 0:
            embed.description = 'No PunkScapes owned :('
            await ctx.send(embed=embed)
            return
        if len(ids) == 1:
            embed.description = f'One PunkScape owned:\n'
        else:
            embed.description = f'{len(ids)} PunkScapes owned (rank in brackets):\n'
        if len(ids) < 35:
            embed.description += ', '.join(
                f'[**{id}**](https://opensea.io/assets/{self.bot.contract_address}/{id}) ({rank})'
                for rank, id in data)
        else:
            embed.description += ', '.join(f'**{id}** ({rank})' for rank, id in data)
        id = data[0][1]
        embed.set_image(url=self.bot.nft_data[id]["external_image"])
        embed.set_footer(text=f'PunkScape #{id}')
        await ctx.send(embed=embed)

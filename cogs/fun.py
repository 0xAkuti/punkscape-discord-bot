from __future__ import annotations

import io
import random
import re
from typing import TYPE_CHECKING, Iterable, List

import cv2
import discord
import numpy as np
from discord.ext import commands
from PIL import Image

if TYPE_CHECKING:
    from bot import PunkScapeBot

PS_WIDTH = 72
PS_HEIGHT = 24


def create_discord_image(img: Image, filename: str):
    with io.BytesIO() as img_binary:
        img.save(img_binary, 'PNG')
        img_binary.seek(0)
        return discord.File(fp=img_binary, filename=filename)

def get_scale(n):
    return min(25, round(50//n**.5))

class Fun(commands.Cog):
    def __init__(self, bot: PunkScapeBot):
        self.bot = bot

    def load_images(self, cmd_ids: Iterable[str]):
        for cmd_id in cmd_ids:
            ids = re.findall('\d+', cmd_id)
            if len(ids) != 1:
                raise ValueError('Invalid id, contains multiple numbers.')
            img = Image.open(self.bot.data_dir / f'images/{int(ids[0])}.png')
            if 'v' in cmd_id:
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
            if 'h' in cmd_id:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            yield img
    
    async def animate_mp4(self, ctx: commands.Context, ids: List[str], scale: int = 10, fps: int = 15):
        imgs = list(self.load_images(ids))
        imgs.append(imgs[0])
        img_merged = Image.new("RGB", (PS_WIDTH * len(imgs), PS_HEIGHT), "black")
        for idx, img in enumerate(imgs):
            img_merged.paste(img, (PS_WIDTH*idx, 0))
        img_merged = img_merged.resize((PS_WIDTH * scale * len(imgs), PS_HEIGHT * scale), Image.NEAREST)
        nr_frames = PS_WIDTH*(len(imgs)-1)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v') # TODO change to avc1
        video = cv2.VideoWriter(str(self.bot.data_dir / 'punkscape_animation.mp4'),
                                fourcc, fps, (PS_WIDTH * scale, PS_HEIGHT * scale))
        for i in range(nr_frames):
            frame = img_merged.crop((i*scale, 0, (i+PS_WIDTH)*scale, PS_HEIGHT*scale))
            video.write(np.array(frame)[..., ::-1])
        video.release()
        await ctx.send(file=discord.File(str(self.bot.data_dir / 'punkscape_animation.mp4')))

    @commands.command()
    async def random(self, ctx: commands.Context):
        await ctx.send(embed=await self.bot.create_punkscape_embed(random.randint(1, 10000)))

    @commands.command()
    async def enjoy(self, ctx: commands.Context, id: int):
        ps = self.bot.nft_data[id]
        embed = discord.Embed(title=f'PunkScape #{id}')
        rarest = sorted(ps['attributes_rarity_scores'].items(),
                        key=lambda x: -x[1])[0][0]
        category, trait = rarest.split(': ')
        if category == 'Attribute Count':
            if ps['attribute_count'] < 5:
                embed.description = 'Wow, so few attributes. Looks clean.'
            else:
                embed.description = 'Wow, so many attributes. Looks rare.'
        else:
            embed.description = f'Wow, nice {trait}.'
        embed.set_image(url=ps['external_image'])
        await ctx.send(embed=embed)

    @commands.command()
    async def merge(self, ctx: commands.Context, *ids: str):
        if not (1 < len(ids) < 101):
            await ctx.send(f'You can merge between 2 and 100 punkscapes.')
            return
        await ctx.trigger_typing()

        scale = get_scale(len(ids))
        img_merged = Image.new("RGB", (PS_WIDTH * len(ids), PS_HEIGHT), "black")
        for idx, img in enumerate(self.load_images(ids)):
            img_merged.paste(img, (PS_WIDTH*idx, 0))
        img_merged = img_merged.resize((PS_WIDTH*scale*len(ids), PS_HEIGHT*scale), Image.NEAREST)
        name_str = '_'.join(map(str, ids))
        await ctx.send(file=create_discord_image(img_merged, f'punkscapes_merge_{name_str}.png'))

    @commands.command()
    async def stack(self, ctx: commands.Context, *ids: str):
        if not (1 < len(ids) < 101):
            await ctx.send(f'You can stack between 2 and 100 punkscapes.')
            return
        await ctx.trigger_typing()

        scale = get_scale(len(ids))
        img_merged = Image.new("RGB", (PS_WIDTH, PS_HEIGHT * len(ids)), "black")
        for idx, img in enumerate(self.load_images(ids)):
            img_merged.paste(img, (0, PS_HEIGHT*idx))
        img_merged = img_merged.resize((PS_WIDTH*scale, PS_HEIGHT*scale*len(ids)), Image.NEAREST)
        name_str = '_'.join(map(str, ids))
        await ctx.send(file=create_discord_image(img_merged, f'punkscapes_stack_{name_str}.png'))

    @commands.command()
    async def grid(self, ctx: commands.Context, x: int, y: int, *ids: str):
        if not (0 < (x * y) < 101):
            await ctx.send(f'You can only combine up 100 PunkScapes.')
            return
        if (x * y) != len(ids):
            await ctx.send(f'Expected {x*y} PunkScapes but got {len(ids)}.')
            return
        await ctx.trigger_typing()

        scale = get_scale(len(ids))
        img_merged = Image.new("RGB", (PS_WIDTH * x, PS_HEIGHT * y), "black")
        for idx, img in enumerate(self.load_images(ids)):
            x_pos = idx % x
            y_pos = idx // x
            img_merged.paste(img, (PS_WIDTH*x_pos, PS_HEIGHT*y_pos))
        img_merged = img_merged.resize((PS_WIDTH*scale*x, PS_HEIGHT*scale*y), Image.NEAREST)
        await ctx.send(file=create_discord_image(img_merged, f'punkscapes_grid_{x}x{y}.png'))

    @commands.command()
    async def scroll(self, ctx: commands.Context, *ids: str):
        if not (1 < len(ids) < 5):
            await ctx.send(f'You can merge between 2 and 4 punkscapes.')
            return
        await ctx.trigger_typing()
        await self.animate_mp4(ctx, ids)

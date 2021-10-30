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

def extract_id(cmd_id):
    if cmd_id == '?':
        return 0
    _ids = re.findall('\d+', cmd_id)
    if len(_ids) != 1:
        raise ValueError('Invalid id, no or contains multiple numbers.')
    return int(_ids[0])

def select_id(scores, used_ids):
    for potential_id in scores.argsort():
        if potential_id not in used_ids and random.randint(0,1):
            return potential_id, scores[potential_id]
class Fun(commands.Cog):
    def __init__(self, bot: PunkScapeBot):
        self.bot = bot
        self.sim = np.array(Image.open(self.bot.data_dir / 'similarity_scores.png'))

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

    async def _merge(self, ctx: commands.Context, *ids: str):
        if not (1 < len(ids) < 101):
            await ctx.send(f'You can merge between 2 and 100 punkscapes.')
            return
        await ctx.trigger_typing()

        scale = get_scale(len(ids))
        img_merged = Image.new("RGB", (PS_WIDTH * len(ids), PS_HEIGHT), "black")
        for idx, img in enumerate(self.load_images(ids)):
            img_merged.paste(img, (PS_WIDTH*idx, 0))
        img_merged = img_merged.resize((PS_WIDTH*scale*len(ids), PS_HEIGHT*scale), Image.NEAREST)
        name_str = '_'.join(map(str, ids[:5]))
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
        name_str = '_'.join(map(str, ids[:5]))
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

    def get_scores(self, prev, prev_flipped, next):
        scores = np.zeros((10000,))
        if prev != 0:
            if prev_flipped: # compare previous start with current start -> S[P, ...]
                scores += self.sim[prev, ..., 0]
            else: # compare previous end with current start -> M[P, ...]
                scores += self.sim[prev, ..., 1]
        if next != '?':
            if 'h' in next: # compare current end with next end -> E[..., N]
                scores += self.sim[..., extract_id(next)-1, 2]
            else: # compare current end with next start -> M[..., N]
                scores += self.sim[..., extract_id(next)-1, 1]
        return scores

    def get_scores_flipped(self, prev, prev_flipped, next):
        scores = np.zeros((10000,))
        if prev != 0:
            if prev_flipped:  # compare previous start with current end -> M[..., P]
                scores += self.sim[..., prev, 1]
            else: # compare previous end with current end -> E[P, ...]
                scores += self.sim[prev, ..., 2]
        if next != '?':
            if 'h' in next: # compare current start with next end -> M[N, ...]
                scores += self.sim[extract_id(next)-1, ..., 1]
            else: # compare current start with next start -> S[..., N]
                scores += self.sim[..., extract_id(next)-1, 0]
        return scores

    @commands.command()
    async def merge(self, ctx: commands.Context, *ids: str):
        if '?' not in ''.join(ids):
            await self._merge(ctx, *ids)
            return
        await ctx.trigger_typing()

        ids = *ids, '?'
        used_ids = set([extract_id(x) for x in ids])
        prev = 0
        flip = False
        command = []
        for current, next in zip(ids, ids[1:]):
            id = 0
            if current == '?':
                if prev != 0 or next != '?':
                    id, score = select_id(self.get_scores(prev, flip, next), used_ids)
                    if score > 50:
                        id_f, score_f = select_id(self.get_scores_flipped(prev, flip, next), used_ids)
                        print(f'N: {id} | {score} || F: {id_f} | {score_f} with next {next}')
                        if score > score_f:
                            id = id_f
                            flip = True
                    else:
                        flip = False
                else:
                    id = random.randint(1, 10000)
                    flip = False
            else:
                id = extract_id(current) - 1
                flip = 'h' in current
            command.append(f'{id+1}{"h" if flip else ""}')
            used_ids.add(id)
            prev = id
        # await ctx.send(f'I rate it {abs(int(10-max(scores)/10))} out of 10')
        await ctx.send(f'{ctx.prefix}merge {" ".join(command)}')
        await self._merge(ctx, *command)
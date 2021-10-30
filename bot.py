import datetime
import json
from collections import defaultdict
from pathlib import Path

import click
import discord
import numpy as np
import yaml
from discord.ext import commands

import cogs
import rarity


def load_punkscapes(path):
    with open(path) as f:
        scapes = {ps['id']: ps for ps in json.load(f)}
    for id in scapes:
        scapes[id]['attribute_count'] = len(scapes[id]['attributes'])-1
    print('Loaded', len(scapes), 'PunkScapes')
    rarity.add_rarity_info(scapes)
    return scapes


def get_dt_dates(punkscapes):
    return np.array([datetime.datetime.fromtimestamp(punkscapes[id]['date'])
                     for id in range(1, 10001)])


def is_general(ctx):
    return isinstance(ctx.channel, discord.channel.TextChannel) and ctx.channel.id == 880032310081228810


class DisabledInChannel(commands.DisabledCommand):
    pass


class PunkScapeBot(commands.Bot):
    def __init__(self, data_path: str, endpoint_url: str, bot_yaml_path: str = 'bot.yaml'):
        with open(bot_yaml_path) as f:
            bot_data = yaml.safe_load(f)
        super().__init__(**bot_data, case_insensitive=True)
        self.before_invoke(self._before_invoke_impl)

        self.nr_calls = defaultdict(int)
        self.data_dir = Path(data_path)
        self.nft_data = load_punkscapes(self.data_dir / 'data.json')
        self.contract_address = bot_data['contract_address']
        self.nft_dates = get_dt_dates(self.nft_data)
        self.add_cog(cogs.Rarity(self, endpoint_url))
        self.add_cog(cogs.Fun(self))
        self.add_cog(cogs.Search(self))
        for command, command_help in bot_data['commands'].items():
            for k, v in command_help.items():
                setattr(self.get_command(command), k, v)
        print('Bot initialized')

    async def on_command_error(self, ctx: commands.Context, error):
        if isinstance(error, DisabledInChannel):
            return
        print(f'ERROR on command {ctx.message!r}: {error!r}')
        await ctx.send(f'Invalid command or argument. Check {ctx.prefix} '
                       f'help to see available commands and how to use them.')

    async def _before_invoke_impl(self, ctx: commands.Context):
        if is_general(ctx) and ctx.command.name != 'enjoy':  # TODO make this configurable
            raise DisabledInChannel
        self.nr_calls['total'] += 1
        self.nr_calls[ctx.command.name] += 1
        if (self.nr_calls['total'] % 100) == 0:
            print(self.nr_calls)

    async def create_punkscape_embed(self, id: int):
        ps = self.nft_data[id]
        embed = discord.Embed(title=f'PunkScape #{id}')
        embed.description = f'Links: [Official](https://punkscape.xyz/scapes/{id}) & ' \
                            f'[Opensea](https://opensea.io/assets/{self.contract_address}/{id})'
        embed.set_image(url=f'https://cdn.punkscape.xyz/scapes/lg/{id}.png')
        embed.add_field(name='Rarity Score', value=ps['rarity_score'])
        embed.add_field(name='Rank', value=f"{ps['rank']+1}/{len(self.nft_data)}")
        embed.add_field(name='Date', value=str(datetime.datetime.fromtimestamp(ps['date'])))
        attributes_list_str = []
        for name, score in sorted(ps['attributes_rarity_scores'].items(), key=lambda x: -x[1]):
            attributes_list_str.append(f' - {name}: {score}')
        embed.add_field(name='Attributes', value='\n'.join(attributes_list_str))
        return embed


@click.command('PunkScape Bot')
@click.option('--bot-token', required=True)
@click.option('--endpoint-url', required=True)
@click.option('--data-dir', type=click.Path(exists=True, file_okay=False))
def main(bot_token: str, endpoint_url: str, data_dir: str):
    bot = PunkScapeBot(data_dir, endpoint_url)
    bot.run(bot_token)


if __name__ == '__main__':
    main(auto_envvar_prefix='PS')

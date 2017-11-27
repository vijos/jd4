from appdirs import user_config_dir
from asyncio import get_event_loop
from os import path
from ruamel import yaml

from jd4.log import logger

_CONFIG_DIR = user_config_dir('jd4')
_CONFIG_FILE = path.join(_CONFIG_DIR, 'config.yaml')

def _load_config():
    try:
        with open(_CONFIG_FILE, encoding='utf-8') as file:
            return yaml.load(file, Loader=yaml.RoundTripLoader)
    except FileNotFoundError:
        logger.error('Config file %s not found.', _CONFIG_FILE)
        exit(1)

config = _load_config()

async def save_config():
    def do_save_config():
        with open(_CONFIG_FILE, 'w', encoding='utf-8') as file:
            yaml.dump(config, file, Dumper=yaml.RoundTripDumper)

    await get_event_loop().run_in_executor(None, do_save_config)

if __name__ == '__main__':
    print(config)

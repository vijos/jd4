from aiohttp import CookieJar
from appdirs import user_config_dir
from asyncio import get_event_loop
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from os import path
from ruamel import yaml

_CONFIG_DIR = user_config_dir('jd4')
_CONFIG_FILE = path.join(_CONFIG_DIR, 'config')
_COOKIES_FILE = path.join(_CONFIG_DIR, 'cookies')

def _load_config():
    with open(_CONFIG_FILE) as file:
        return yaml.load(file, Loader=yaml.RoundTripLoader)

config = _load_config()

cookie_jar = CookieJar()
try:
    cookie_jar.load(_COOKIES_FILE)
except FileNotFoundError:
    pass

_executor = ThreadPoolExecutor()

async def save_config():
    def do_save_config():
        with open(_CONFIG_FILE, 'w') as file:
            yaml.dump(config, file, Dumper=yaml.RoundTripDumper)

    await get_event_loop().run_in_executor(_executor, do_save_config)

_save_cookie_function = partial(cookie_jar.save, _COOKIES_FILE)

async def save_cookies():
    await get_event_loop().run_in_executor(_executor, _save_cookie_function)

if __name__ == '__main__':
    print(config)
    print(list(cookie_jar))

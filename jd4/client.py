import json
import yaml
from aiohttp import ClientSession, CookieJar
from asyncio import get_event_loop, sleep
from appdirs import user_cache_dir, user_config_dir
from os import makedirs, path
from urllib.parse import urljoin

from jd4.log import logger

CACHE_DIR = user_cache_dir('jd4')
CONFIG_DIR = user_config_dir('jd4')
SERVER_URL = 'https://vijos.org'
RETRY_DELAY_SEC = 30
CHUNK_SIZE = 32768

def full_url(*parts):
    return urljoin(SERVER_URL, path.join(*parts))

class VJ4Error(Exception):
    def __init__(self, name, message, *args):
        super().__init__('{}: {} ({})'.format(name, message, ', '.join(map(str, args))))
        self.name = name
        self.message = message
        self.args = args

# TODO(iceboy): The save is actually blocking.
class PersistentCookieJar(CookieJar):
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        if path.exists(file_path):
            self.load(file_path)

    def clear(self):
        super().clear()
        self.save(self.file_path)

    def update_cookies(self, cookies, response_url):
        super().update_cookies(cookies, response_url)
        self.save(self.file_path)

class VJ4Session(ClientSession):
    def __init__(self):
        super().__init__(cookie_jar=PersistentCookieJar(path.join(CONFIG_DIR, 'cookies')))

        self.data_timestamp = 0

    async def call(self, relative_url, **kwargs):
        if not kwargs:
            verb = 'GET'
        else:
            verb = 'POST'
        async with super().request(verb,
                                   full_url(relative_url),
                                   headers={'accept': 'application/json'},
                                   allow_redirects=False,
                                   data=kwargs) as response:
            if response.content_type != 'application/json':
                raise Exception('invalid content type')
            response_dict = await response.json()
            if 'error' in response_dict:
                error = response_dict['error']
                raise VJ4Error(error.get('name', 'unknown'), error.get('message', ''), *error.get('args', []))
            return response_dict

    async def judge_consume(self):
        async with self.ws_connect(full_url('judge/consume-conn/websocket')) as ws:
            logger.info('Connected')
            async for msg in ws:
                logger.info(json.loads(msg.data))
            logger.warning('Connection lost with code %d', ws.close_code)

    async def judge_noop(self):
        await self.call('judge/noop')

    async def login(self, uname, password):
        logger.info('Login')
        await self.call('login', uname=uname, password=password)

    async def login_if_needed(self, uname, password):
        try:
            await self.judge_noop()
            logger.info('Session is valid')
        except VJ4Error as e:
            if e.name == 'PrivilegeError':
                await self.login(uname, password)
            else:
                raise

    async def problem_data(self, domain_id, pid, save_path):
        logger.info('Getting problem data: %s, %s', domain_id, pid)
        loop = get_event_loop()
        async with super().get(full_url('d', domain_id, 'p', pid, 'data'),
                               headers={'accept': 'application/json'}) as response:
            if response.content_type == 'application/json':
                response_dict = await response.json()
                if 'error' in response_dict:
                    error = response_dict['error']
                    raise VJ4Error(error.get('name', 'unknown'),
                                   error.get('message', ''),
                                   *error.get('args', []))
                raise Exception('unexpected response')
            if response.status != 200:
                raise Exception('http error ' + str(response.status))
            with open(save_path, 'wb') as save_file:
                while True:
                    buffer = await response.content.read(CHUNK_SIZE)
                    if not buffer:
                        break
                    await loop.run_in_executor(None, save_file.write, buffer)

if __name__ == '__main__':
    makedirs(CACHE_DIR, exist_ok=True)
    makedirs(CONFIG_DIR, exist_ok=True)
    with open(path.join(CONFIG_DIR, 'config')) as config_file:
        config = yaml.load(config_file) or {}

    async def main():
        async with VJ4Session() as session:
            while True:
                try:
                    await session.login_if_needed(config['uname'], config['password'])
                    # TODO(iceboy): download data
                    await session.judge_consume()
                except Exception as e:
                    logger.exception(e)
                logger.info('Retrying after %d seconds', RETRY_DELAY_SEC)
                await sleep(RETRY_DELAY_SEC)

    get_event_loop().run_until_complete(main())

import json
from aiohttp import ClientSession
from asyncio import get_event_loop, sleep
from appdirs import user_cache_dir
from os import makedirs, path
from urllib.parse import urljoin

from jd4.config import config, cookie_jar, save_config, save_cookies
from jd4.log import logger

CACHE_DIR = user_cache_dir('jd4')
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

async def json_response_to_dict(response):
    if response.content_type != 'application/json':
        raise Exception('invalid content type ' + response.content_type)
    response_dict = await response.json()
    if 'error' in response_dict:
        error = response_dict['error']
        raise VJ4Error(error.get('name', 'unknown'), error.get('message', ''), *error.get('args', []))
    return response_dict

class VJ4Session(ClientSession):
    async def get_json(self, relative_url, **kwargs):
        async with super().get(full_url(relative_url),
                                headers={'accept': 'application/json'},
                                allow_redirects=False,
                                params=kwargs) as response:
            return await json_response_to_dict(response)

    async def post_json(self, relative_url, **kwargs):
        async with super().post(full_url(relative_url),
                                headers={'accept': 'application/json'},
                                allow_redirects=False,
                                data=kwargs) as response:
            return await json_response_to_dict(response)

    async def judge_consume(self):
        async with self.ws_connect(full_url('judge/consume-conn/websocket')) as ws:
            logger.info('Connected')
            async for msg in ws:
                logger.info(json.loads(msg.data))
            logger.warning('Connection lost with code %d', ws.close_code)

    async def judge_noop(self):
        await self.get_json('judge/noop')

    async def login(self, uname, password):
        logger.info('Login')
        await self.post_json('login', uname=uname, password=password)

    async def login_if_needed(self, uname, password):
        try:
            await self.judge_noop()
            logger.info('Session is valid')
        except VJ4Error as e:
            if e.name == 'PrivilegeError':
                await self.login(uname, password)
            else:
                raise

    async def judge_datalist(self, last):
        return await self.get_json('judge/datalist', last=last)

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

    async def main():
        async with VJ4Session(cookie_jar=cookie_jar) as session:
            while True:
                try:
                    await session.login_if_needed(config['uname'], config['password'])
                    await save_cookies()
                    # TODO(iceboy): download data
                    await session.judge_consume()
                except Exception as e:
                    logger.exception(e)
                logger.info('Retrying after %d seconds', RETRY_DELAY_SEC)
                await sleep(RETRY_DELAY_SEC)

    get_event_loop().run_until_complete(main())

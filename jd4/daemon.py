from asyncio import get_event_loop, sleep

from jd4.api import VJ4Session
from jd4.config import config
from jd4.log import logger

RETRY_DELAY_SEC = 30

async def daemon():
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

if __name__ == '__main__':
    get_event_loop().run_until_complete(daemon())

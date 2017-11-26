from asyncio import gather, get_event_loop, LifoQueue, Lock

from jd4.config import config
from jd4.log import logger
from jd4.sandbox import create_sandboxes

_lock = Lock()
_queue = LifoQueue()

async def get_sandbox(n):
    await _lock.acquire()
    try:
        return await gather(*list(_queue.get() for _ in range(n)))
    finally:
        _lock.release()

def put_sandbox(*sandboxes):
    for sandbox in sandboxes:
        _queue.put_nowait(sandbox)

async def _init():
    parallelism = config.get('parallelism', 2)
    if parallelism < 2:
        logger.warning('Parallelism less than 2, custom judge will not be supported.')
    logger.info('Using parallelism: %d', parallelism)
    put_sandbox(*await create_sandboxes(parallelism))

get_event_loop().run_until_complete(_init())

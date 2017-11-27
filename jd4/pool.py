from asyncio import gather, get_event_loop, LifoQueue, Lock

from jd4.config import config
from jd4.log import logger
from jd4.sandbox import create_sandboxes

async def get_sandbox(n):
    await _lock.acquire()
    try:
        return await gather(*list(_queue.get() for _ in range(n)))
    finally:
        _lock.release()

def put_sandbox(*sandboxes):
    for sandbox in sandboxes:
        _queue.put_nowait(sandbox)

def _init():
    parallelism = config.get('parallelism', 2)
    if parallelism < 2:
        logger.warning('Parallelism less than 2, custom judge will not be supported.')
    logger.info('Using parallelism: %d', parallelism)
    sandboxes_task = create_sandboxes(parallelism)
    global _lock, _queue
    _lock = Lock()
    _queue = LifoQueue()
    put_sandbox(*get_event_loop().run_until_complete(sandboxes_task))

_init()

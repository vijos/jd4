from appdirs import user_cache_dir
from asyncio import get_event_loop
from os import makedirs, path, unlink

_CACHE_DIR = user_cache_dir('jd4')

async def cache_open(session, domain_id, pid):
    domain_dir = path.join(_CACHE_DIR, domain_id)
    makedirs(domain_dir, exist_ok=True)
    file_path = path.join(domain_dir, pid + '.zip')
    while True:
        try:
            file = open(file_path, 'rb')
            return file
        except FileNotFoundError:
            pass
        await session.problem_data(domain_id, pid, file_path)

async def cache_invalidate(domain_id, pid):
    loop = get_event_loop()
    file_path = path.join(_CACHE_DIR, domain_id, pid + '.zip')
    try:
        await loop.run_in_executor(None, unlink, file_path)
    except FileNotFoundError:
        pass

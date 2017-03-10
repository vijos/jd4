from asyncio import gather, get_event_loop, sleep

from jd4.api import VJ4Session
from jd4.case import read_legacy_cases
from jd4.cache import cache_open, cache_invalidate
from jd4.cgroup import try_init_cgroup
from jd4.config import config
from jd4.langs import langs
from jd4.log import logger
from jd4.sandbox import create_sandbox

RETRY_DELAY_SEC = 30

try_init_cgroup()
loop = get_event_loop()
sandbox = loop.run_until_complete(create_sandbox())

class DaemonSession(VJ4Session):
    async def do_judge(self, request, ws):
        tag = request['tag']
        # TODO(iceboy)
        if request['type'] != 0:
            raise RuntimeError('unsupported type ' + str(request['type']))
        build = langs.get(request['lang'])
        if not build:
            # TODO(iceboy)
            raise RuntimeError('lang ' + request['lang'] + ' not found')
        if request['pid'] != '1000':
            raise RuntimeError('not a+b')
        file, (build_status, package) = await gather(
            cache_open(self, request['domain_id'], request['pid']),
            build(sandbox, request['code'].encode()))
        cases = list(read_legacy_cases(file))
        # TODO(iceboy): Handle compile error.
        if build_status:
            raise RuntimeError('compile error')
        total_status = 0
        total_score = 0
        total_time_usage_ns = 0
        total_memory_usage_bytes = 0
        for index, case in enumerate(cases):
            status, score, time_usage_ns, memory_usage_bytes, stderr = await case.judge(sandbox, package)
            ws.send_json({'key': 'next',
                          'tag': tag,
                          'case': {
                              'status': status,
                              'score': score,
                              'time_ms': int(time_usage_ns / 1000000),
                              'memory_kb': int(memory_usage_bytes / 1024),
                              'judge_text': stderr.decode(),
                          }})
            total_status = max(total_status, status)
            total_score += score
            total_time_usage_ns += time_usage_ns
            total_memory_usage_bytes = max(total_memory_usage_bytes, memory_usage_bytes)
        ws.send_json({'key': 'end',
                      'tag': tag,
                      'status': total_status,
                      'score': total_score,
                      'time_ms': int(total_memory_usage_bytes / 1000000),
                      'memory_kb': int(total_memory_usage_bytes / 1024)})
        file.close()

async def daemon():
    async with DaemonSession() as session:
        await cache_invalidate('system', '1000')
        while True:
            try:
                await session.login_if_needed(config['uname'], config['password'])
                await session.judge_consume()
            except Exception as e:
                logger.exception(e)
            logger.info('Retrying after %d seconds', RETRY_DELAY_SEC)
            await sleep(RETRY_DELAY_SEC)

# TODO(iceboy): maintain cache (invalidate, background download).
loop.run_until_complete(daemon())

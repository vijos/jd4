from asyncio import gather, get_event_loop, sleep
from io import BytesIO

from jd4.api import VJ4Session
from jd4.case import read_legacy_cases
from jd4.cache import cache_open, cache_invalidate
from jd4.cgroup import try_init_cgroup
from jd4.config import config, save_config, try_get_int
from jd4.langs import langs
from jd4.log import logger
from jd4.sandbox import create_sandbox
from jd4.status import STATUS_COMPILE_ERROR, STATUS_SYSTEM_ERROR

RETRY_DELAY_SEC = 30

try_init_cgroup()
loop = get_event_loop()
sandbox = loop.run_until_complete(create_sandbox())

class CompileError(Exception):
    pass

class SystemError(Exception):
    pass

class JudgeHandler:
    def __init__(self, session, request, ws):
        self.session = session
        self.request = request
        self.ws = ws
        self.tag = self.request.pop('tag', None)

    async def handle(self):
        try:
            event = self.request.pop('event', None)
            if event:
                if event == 'problem_data_change':
                    await self.update_problem_data()
                else:
                    raise SystemError('Unknown event: {}'.format(event))
            else:
                type = self.request.pop('type')
                if type == 0:
                    await self.submission()
                elif type == 1:
                    await self.pretest()
                else:
                    raise SystemError('Unsupported type: {}'.format(type))
            for key in self.request:
                logger.warning('Unused key in judge request: %s', key)
        except CompileError:
            self.end(status=STATUS_COMPILE_ERROR, score=0, time_ms=0, memory_kb=0)
        except Exception as e:
            logger.exception(e)
            self.end(status=STATUS_SYSTEM_ERROR, score=0, time_ms=0, memory_kb=0)

    async def update_problem_data(self):
        domain_id = self.request.pop('domain_id')
        pid = str(self.request.pop('pid'))
        await cache_invalidate(domain_id, pid)
        logger.debug('Invalidated %s/%s', domain_id, pid)
        await update_problem_data(self.session)

    async def submission(self):
        domain_id = self.request.pop('domain_id')
        pid = self.request.pop('pid')
        logger.info('Submission: %s, %s', domain_id, pid)
        cases_file, package = await gather(cache_open(self.session, domain_id, pid), self.build())
        try:
            await self.judge(cases_file, package)
        finally:
            cases_file.close()

    async def pretest(self):
        rid = self.request.pop('rid')
        logger.info('Pretest: %s', rid)
        cases_data, package = await gather(self.session.record_pretest_data(rid), self.build())
        await self.judge(BytesIO(cases_data), package)

    async def build(self):
        lang = self.request.pop('lang')
        build_fn = langs.get(lang)
        if not build_fn:
            raise SystemError('Unsupported language: {}'.format(lang))
        package, message = await build_fn(sandbox, self.request.pop('code').encode())
        self.next(compiler_text=message)
        if not package:
            raise CompileError('Compile error: {}'.format(message))
        return package

    async def judge(self, cases_file, package):
        cases = list(read_legacy_cases(cases_file))
        total_status = 0
        total_score = 0
        total_time_usage_ns = 0
        total_memory_usage_bytes = 0
        for index, case in enumerate(cases):
            status, score, time_usage_ns, memory_usage_bytes, stderr = await case.judge(sandbox, package)
            self.next(case={'status': status,
                            'score': score,
                            'time_ms': time_usage_ns // 1000000,
                            'memory_kb': memory_usage_bytes // 1024,
                            'judge_text': stderr.decode()}, progress=(index + 1) / len(cases))
            total_status = max(total_status, status)
            total_score += score
            total_time_usage_ns += time_usage_ns
            total_memory_usage_bytes = max(total_memory_usage_bytes, memory_usage_bytes)
        self.end(status=total_status,
                 score=total_score,
                 time_ms=total_time_usage_ns // 1000000,
                 memory_kb=total_memory_usage_bytes // 1024)

    def next(self, **kwargs):
        self.ws.send_json({'key': 'next', 'tag': self.tag, **kwargs})

    def end(self, **kwargs):
        self.ws.send_json({'key': 'end', 'tag': self.tag, **kwargs})


async def update_problem_data(session):
    ''' Invalidate all expired data. '''
    logger.info('Update problem data')
    result = await session.judge_datalist(try_get_int('last_update_at'))
    for pid in result['pids']:
      await cache_invalidate(pid['domain_id'], pid['pid'])
      logger.debug('Invalidated %s/%s', pid['domain_id'], str(pid['pid']))
    config['last_update_at'] = str(result['time'])
    await save_config()


async def daemon():
    async with VJ4Session(config['server']) as session:
        while True:
            try:
                await session.login_if_needed(config['uname'], config['password'])
                await update_problem_data(session)
                await session.judge_consume(JudgeHandler)
            except Exception as e:
                logger.exception(e)
            logger.info('Retrying after %d seconds', RETRY_DELAY_SEC)
            await sleep(RETRY_DELAY_SEC)

# TODO(iceboy): maintain cache (invalidate, background download).
loop.run_until_complete(daemon())

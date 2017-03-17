from asyncio import get_event_loop, sleep
from io import BytesIO

from jd4.api import VJ4Session
from jd4.case import read_legacy_cases
from jd4.cache import cache_open, cache_invalidate
from jd4.cgroup import try_init_cgroup
from jd4.config import config, save_config
from jd4.log import logger
from jd4.pool import pool_build, pool_judge
from jd4.status import STATUS_COMPILE_ERROR, STATUS_SYSTEM_ERROR, STATUS_JUDGING, STATUS_COMPILING

RETRY_DELAY_SEC = 30

class CompileError(Exception):
    def __init__(self, message, time_usage_ns, memory_usage_bytes):
        super().__init__(message)
        self.time_usage_ns = time_usage_ns
        self.memory_usage_bytes = memory_usage_bytes

class SystemError(Exception):
    pass

class JudgeHandler:
    def __init__(self, session, request, ws):
        self.session = session
        self.request = request
        self.ws = ws
        self.tag = self.request.pop('tag', None)
        self.event = self.request.pop('event', None)
        self.type = self.request.pop('type', None)

    async def handle(self):
        try:
            if self.event:
                if self.event == 'problem_data_change':
                    await self.update_problem_data()
                else:
                    raise SystemError('Unknown event: {}'.format(self.event))
            else:
                if self.type == 0:
                    await self.submission()
                elif self.type == 1:
                    await self.pretest()
                else:
                    raise SystemError('Unsupported type: {}'.format(self.type))
            for key in self.request:
                logger.warning('Unused key in judge request: %s', key)
        except CompileError as e:
            self.end(status=STATUS_COMPILE_ERROR,
                     score=0,
                     time_ms=e.time_usage_ns // 1000000,
                     memory_kb=e.memory_usage_bytes // 1024)
        except Exception as e:
            logger.exception(e)
            self.next(judge_text=repr(e))
            self.end(status=STATUS_SYSTEM_ERROR, score=0, time_ms=0, memory_kb=0)

    async def update_problem_data(self):
        domain_id = self.request.pop('domain_id')
        pid = str(self.request.pop('pid'))
        await cache_invalidate(domain_id, pid)
        logger.debug('Invalidated %s/%s', domain_id, pid)
        await update_problem_data(self.session)

    async def submission(self):
        loop = get_event_loop()
        domain_id = self.request.pop('domain_id')
        pid = self.request.pop('pid')
        rid = self.request.pop('rid')
        logger.info('Submission: %s, %s, %s', domain_id, pid, rid)
        cases_file_task = loop.create_task(cache_open(self.session, domain_id, pid))
        package = await self.build()
        with await cases_file_task as cases_file:
            await self.judge(cases_file, package)

    async def pretest(self):
        loop = get_event_loop()
        domain_id = self.request.pop('domain_id')
        pid = self.request.pop('pid')
        rid = self.request.pop('rid')
        logger.info('Pretest: %s, %s, %s', domain_id, pid, rid)
        cases_data_task = loop.create_task(self.session.record_pretest_data(rid))
        package = await self.build()
        with BytesIO(await cases_data_task) as cases_file:
            await self.judge(cases_file, package)

    async def build(self):
        self.next(status=STATUS_COMPILING)
        lang = self.request.pop('lang')
        code = self.request.pop('code')
        package, message, time_usage_ns, memory_usage_bytes = await pool_build(lang, code)
        self.next(compiler_text=message)
        if not package:
            logger.debug('Compile error: %s', message)
            raise CompileError(message, time_usage_ns, memory_usage_bytes)
        return package

    async def judge(self, cases_file, package):
        loop = get_event_loop()
        self.next(status=STATUS_JUDGING, progress=0)
        cases = list(read_legacy_cases(cases_file))
        total_status = 0
        total_score = 0
        total_time_usage_ns = 0
        total_memory_usage_bytes = 0
        judge_tasks = list()
        for case in cases:
            judge_tasks.append(loop.create_task(pool_judge(package, case)))
        for index, judge_task in enumerate(judge_tasks):
            status, score, time_usage_ns, memory_usage_bytes, stderr = await judge_task
            case = {'status': status,
                    'score': score,
                    'time_ms': time_usage_ns // 1000000,
                    'memory_kb': memory_usage_bytes // 1024}
            if self.type == 1:
                case['judge_text'] = stderr.decode(encoding='utf-8', errors='replace')
            else:
                case['judge_text'] = ''
            self.next(status=STATUS_JUDGING,
                      case=case,
                      progress=(index + 1) * 100 // len(cases))
            logger.debug('Case %d: %d, %g, %g, %g, %s',
                         index, status, score, time_usage_ns / 1000000, memory_usage_bytes / 1024, stderr)
            total_status = max(total_status, status)
            total_score += score
            total_time_usage_ns += time_usage_ns
            total_memory_usage_bytes = max(total_memory_usage_bytes, memory_usage_bytes)
        self.end(status=total_status,
                 score=total_score,
                 time_ms=total_time_usage_ns // 1000000,
                 memory_kb=total_memory_usage_bytes // 1024)
        logger.info('Total: %d, %g, %g, %g',
                    total_status, total_score, total_time_usage_ns / 1000000, total_memory_usage_bytes / 1024)

    def next(self, **kwargs):
        self.ws.send_json({'key': 'next', 'tag': self.tag, **kwargs})

    def end(self, **kwargs):
        self.ws.send_json({'key': 'end', 'tag': self.tag, **kwargs})

async def update_problem_data(session):
    logger.info('Update problem data')
    result = await session.judge_datalist(config.get('last_update_at', 0))
    for pid in result['pids']:
        await cache_invalidate(pid['domain_id'], str(pid['pid']))
        logger.debug('Invalidated %s/%s', pid['domain_id'], str(pid['pid']))
    config['last_update_at'] = result['time']
    await save_config()

async def daemon():
    try_init_cgroup()

    async with VJ4Session(config['server_url']) as session:
        while True:
            try:
                await session.login_if_needed(config['uname'], config['password'])
                await update_problem_data(session)
                await session.judge_consume(JudgeHandler)
            except Exception as e:
                logger.exception(e)
            logger.info('Retrying after %d seconds', RETRY_DELAY_SEC)
            await sleep(RETRY_DELAY_SEC)

get_event_loop().run_until_complete(daemon())

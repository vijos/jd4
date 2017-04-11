import shlex
from appdirs import user_config_dir
from asyncio import gather, get_event_loop, LifoQueue
from functools import partial
from os import mkfifo, path
from ruamel import yaml
from socket import socket, AF_UNIX, SOCK_STREAM, SOCK_NONBLOCK

from jd4.cgroup import wait_cgroup
from jd4.compile import Compiler, Interpreter
from jd4.config import config
from jd4.log import logger
from jd4.sandbox import create_sandboxes
from jd4.util import read_pipe

_CONFIG_DIR = user_config_dir('jd4')
_LANGS_FILE = path.join(_CONFIG_DIR, 'langs.yaml')
_MAX_OUTPUT = 8192
DEFAULT_TIME_MS = 20000
DEFAULT_MEM_KB = 262144
PROCESS_LIMIT = 32

_sandbox_pool = LifoQueue()
_langs = dict()

async def _compiler_build(compiler, code,
                          time_limit_ns, memory_limit_bytes, process_limit):
    loop = get_event_loop()
    sandbox = await _sandbox_pool.get()
    try:
        await compiler.prepare(sandbox, code.encode())
        output_file = path.join(sandbox.in_dir, 'output')
        mkfifo(output_file)
        with socket(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK) as cgroup_sock:
            cgroup_sock.bind(path.join(sandbox.in_dir, 'cgroup'))
            cgroup_sock.listen()
            build_task = loop.create_task(compiler.build(
                sandbox,
                output_file='/in/output',
                cgroup_file='/in/cgroup'))
            others_task = gather(read_pipe(output_file, _MAX_OUTPUT),
                                 wait_cgroup(cgroup_sock,
                                             build_task,
                                             time_limit_ns,
                                             memory_limit_bytes,
                                             process_limit))
            package, status = await build_task
            output, (time_usage_ns, memory_usage_bytes) = await others_task
        return package, output.decode(encoding='utf-8', errors='replace'), \
               time_usage_ns, memory_usage_bytes
    finally:
        _sandbox_pool.put_nowait(sandbox)

async def _interpreter_build(interpreter, code):
    return interpreter.build(code.encode()), '', 0, 0

async def _init():
    parallelism = config.get('parallelism', 1)
    logger.info('Using parallelism: %d', parallelism)
    for sandbox in await create_sandboxes(parallelism):
        _sandbox_pool.put_nowait(sandbox)

    try:
        with open(_LANGS_FILE) as file:
            langs_config = yaml.load(file, Loader=yaml.RoundTripLoader)
    except FileNotFoundError:
        logger.error('Language file %s not found.', _LANGS_FILE)
        exit(1)
    for lang_name, lang_config in langs_config.items():
        if lang_config['type'] == 'compiler':
            compiler = Compiler(lang_config['compiler_file'],
                                shlex.split(lang_config['compiler_args']),
                                lang_config['code_file'],
                                lang_config['execute_file'],
                                shlex.split(lang_config['execute_args']))
            _langs[lang_name] = partial(
                _compiler_build, compiler,
                time_limit_ns=lang_config.get('time_limit_ms', DEFAULT_TIME_MS) * 1000000,
                memory_limit_bytes=lang_config.get('memory_limit_kb', DEFAULT_MEM_KB) * 1024,
                process_limit=lang_config.get('process_limit', PROCESS_LIMIT))
        elif lang_config['type'] == 'interpreter':
            interpreter = Interpreter(lang_config['code_file'],
                                      lang_config['execute_file'],
                                      shlex.split(lang_config['execute_args']))
            _langs[lang_name] = partial(_interpreter_build, interpreter)
        else:
            logger.error('Unknown type %s', lang_config['type'])

async def pool_build(lang, code):
    build_fn = _langs.get(lang)
    if not build_fn:
        raise SystemError('Unsupported language: {}'.format(lang))
    return await build_fn(code)

async def pool_judge(package, case):
    sandbox = await _sandbox_pool.get()
    try:
        return await case.judge(sandbox, package)
    finally:
        _sandbox_pool.put_nowait(sandbox)

get_event_loop().run_until_complete(_init())

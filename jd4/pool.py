import shlex
from appdirs import user_config_dir
from asyncio import get_event_loop, LifoQueue
from functools import partial
from os import mkfifo, path
from ruamel import yaml

from jd4.compile import Compiler, Interpreter
from jd4.config import config
from jd4.log import logger
from jd4.sandbox import create_sandboxes
from jd4.util import read_pipe

_CONFIG_DIR = user_config_dir('jd4')
_LANGS_FILE = path.join(_CONFIG_DIR, 'langs.yaml')
_MAX_OUTPUT = 8192

_sandbox_pool = LifoQueue()
_langs = dict()

async def _compiler_build(compiler, code):
    loop = get_event_loop()
    sandbox = await _sandbox_pool.get()
    try:
        await compiler.prepare(sandbox, code)
        output_file = path.join(sandbox.in_dir, 'output')
        mkfifo(output_file)
        output_task = loop.create_task(read_pipe(output_file, _MAX_OUTPUT))
        package, status = await compiler.build(sandbox, stdout_file='/in/output', stderr_file='/in/output')
        output = await output_task
        return package, output.decode(encoding='utf-8', errors='replace')
    finally:
        _sandbox_pool.put_nowait(sandbox)

async def _interpreter_build(interpreter, code):
    return interpreter.build(code), None

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
            _langs[lang_name] = partial(_compiler_build, compiler)
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

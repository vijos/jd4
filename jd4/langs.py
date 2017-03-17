import shlex
from appdirs import user_config_dir
from asyncio import gather
from functools import partial
from os import mkfifo, path
from ruamel import yaml

from jd4.compile import Compiler, Interpreter
from jd4.cgroup import CGroup, accept_and_limit, PROCESS_LIMIT, DEFAULT_TIME_MS, DEFAULT_MEM_KB
from jd4.log import logger
from jd4.util import read_pipe

_CONFIG_DIR = user_config_dir('jd4')
_LANGS_FILE = path.join(_CONFIG_DIR, 'langs.yaml')
_MAX_OUTPUT = 8192

async def _compiler_build(compiler, sandbox, code,
                          time_limit_ns, memory_limit_bytes, process_limit):
    await compiler.prepare(sandbox, code)
    output_file = path.join(sandbox.in_dir, 'output')
    mkfifo(output_file)
    cgroup = CGroup(path.join(sandbox.in_dir, 'cgroup'))
    try:
        (package, status), output, (exit_event, usage_future) = await gather(
            compiler.build(sandbox,
                           stdout_file='/in/output',
                           stderr_file='/in/output',
                           cgroup_file='/in/cgroup'),
            read_pipe(output_file, _MAX_OUTPUT),
            accept_and_limit(cgroup, time_limit_ns, memory_limit_bytes, process_limit))
        exit_event.set()
        time_usage_ns, memory_usage_bytes = await usage_future
    finally:
            cgroup.close()
    return package, output.decode(encoding='utf-8', errors='replace'), \
           time_usage_ns, memory_usage_bytes

async def _interpreter_build(interpreter, _, code):
    return interpreter.build(code), None, 0, 0

def _load_langs():
    try:
        with open(_LANGS_FILE) as file:
            langs_config = yaml.load(file, Loader=yaml.RoundTripLoader)
    except FileNotFoundError:
        logger.error('Language file %s not found.', _LANGS_FILE)
        exit(1)
    langs = dict()
    for lang_name, lang_config in langs_config.items():
        if lang_config['type'] == 'compiler':
            compiler = Compiler(lang_config['compiler_file'],
                                shlex.split(lang_config['compiler_args']),
                                lang_config['code_file'],
                                lang_config['execute_file'],
                                shlex.split(lang_config['execute_args']))
            langs[lang_name] = partial(
                _compiler_build, compiler,
                time_limit_ns=lang_config.get('time_limit_ms', DEFAULT_TIME_MS) * 1000000,
                memory_limit_bytes=lang_config.get('memory_limit_kb', DEFAULT_MEM_KB) * 1024,
                process_limit=lang_config.get('process_limit', PROCESS_LIMIT))
        elif lang_config['type'] == 'interpreter':
            interpreter = Interpreter(lang_config['code_file'],
                                      lang_config['execute_file'],
                                      shlex.split(lang_config['execute_args']))
            langs[lang_name] = partial(_interpreter_build, interpreter)
        else:
            logger.error('Unknown type %s', lang_config['type'])
    return langs

langs = _load_langs()

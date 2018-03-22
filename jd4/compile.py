import shlex
from appdirs import user_config_dir
from asyncio import gather, get_event_loop
from functools import partial
from ruamel import yaml
from socket import socket, AF_UNIX, SOCK_STREAM, SOCK_NONBLOCK
from os import mkdir, mkfifo, path
from shutil import copytree, rmtree
from tempfile import mkdtemp

from jd4.cgroup import wait_cgroup
from jd4.log import logger
from jd4.pool import get_sandbox, put_sandbox
from jd4.sandbox import SANDBOX_COMPILE, SANDBOX_EXECUTE
from jd4.util import parse_memory_bytes, parse_time_ns, \
                     read_pipe, write_binary_file

_MAX_OUTPUT = 8192
DEFAULT_TIME = '20s'
DEFAULT_MEMORY = '256m'
PROCESS_LIMIT = 64
_CONFIG_DIR = user_config_dir('jd4')
_LANGS_FILE = path.join(_CONFIG_DIR, 'langs.yaml')
_langs = dict()

class Executable:
    def __init__(self, execute_file, execute_args):
        self.execute_file = execute_file
        self.execute_args = execute_args

    async def execute(self, sandbox, *,
                      stdin_file=None,
                      stdout_file=None,
                      stderr_file=None,
                      extra_file=None,
                      cgroup_file=None):
        return await sandbox.call(SANDBOX_EXECUTE,
                                  self.execute_file,
                                  self.execute_args,
                                  stdin_file,
                                  stdout_file,
                                  stderr_file,
                                  extra_file,
                                  cgroup_file)

class Package:
    def __init__(self, package_dir, execute_file, execute_args):
        self.package_dir = package_dir
        self.execute_file = execute_file
        self.execute_args = execute_args

    def __del__(self):
        rmtree(self.package_dir)

    async def install(self, sandbox):
        loop = get_event_loop()
        await sandbox.reset()
        await loop.run_in_executor(None,
                                   copytree,
                                   path.join(self.package_dir, 'package'),
                                   path.join(sandbox.in_dir, 'package'))
        return Executable(self.execute_file, self.execute_args)

class Compiler:
    def __init__(self,
                 compiler_file,
                 compiler_args,
                 code_file,
                 execute_file,
                 execute_args):
        self.compiler_file = compiler_file
        self.compiler_args = compiler_args
        self.code_file = code_file
        self.execute_file = execute_file
        self.execute_args = execute_args

    async def prepare(self, sandbox, code):
        loop = get_event_loop()
        await sandbox.reset()
        await loop.run_in_executor(None,
                                   write_binary_file,
                                   path.join(sandbox.in_dir, self.code_file),
                                   code)

    async def build(self, sandbox, *, output_file=None, cgroup_file=None):
        loop = get_event_loop()
        status = await sandbox.call(SANDBOX_COMPILE,
                                    self.compiler_file,
                                    self.compiler_args,
                                    output_file,
                                    cgroup_file)
        if status:
            return None, status
        package_dir = mkdtemp(prefix='jd4.package.')
        await loop.run_in_executor(None,
                                   copytree,
                                   sandbox.out_dir,
                                   path.join(package_dir, 'package'))
        return Package(package_dir, self.execute_file, self.execute_args), 0

class Interpreter:
    def __init__(self, code_file, execute_file, execute_args):
        self.code_file = code_file
        self.execute_file = execute_file
        self.execute_args = execute_args

    def build(self, code):
        package_dir = mkdtemp(prefix='jd4.package.')
        mkdir(path.join(package_dir, 'package'))
        write_binary_file(path.join(package_dir, 'package', self.code_file),
                          code)
        return Package(package_dir, self.execute_file, self.execute_args)

async def _compiler_build(compiler,
                          time_limit_ns,
                          memory_limit_bytes,
                          process_limit,
                          code):
    loop = get_event_loop()
    sandbox, = await get_sandbox(1)
    try:
        await compiler.prepare(sandbox, code)
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
                                             time_limit_ns,
                                             memory_limit_bytes,
                                             process_limit))
            package, status = await build_task
            output, (time_usage_ns, memory_usage_bytes) = await others_task
        return package, output.decode(encoding='utf-8', errors='replace'), \
               time_usage_ns, memory_usage_bytes
    finally:
        put_sandbox(sandbox)

async def _interpreter_build(interpreter, code):
    return interpreter.build(code), '', 0, 0

async def build(lang, code):
    build_fn = _langs.get(lang)
    if not build_fn:
        raise SystemError('Unsupported language: {}'.format(lang))
    return await build_fn(code)

def _init():
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
                _compiler_build,
                compiler,
                parse_time_ns(lang_config.get('time', DEFAULT_TIME)),
                parse_memory_bytes(lang_config.get('memory', DEFAULT_MEMORY)),
                lang_config.get('process_limit', PROCESS_LIMIT))
        elif lang_config['type'] == 'interpreter':
            interpreter = Interpreter(lang_config['code_file'],
                                      lang_config['execute_file'],
                                      shlex.split(lang_config['execute_args']))
            _langs[lang_name] = partial(_interpreter_build, interpreter)
        else:
            logger.error('Unknown type %s', lang_config['type'])

_init()

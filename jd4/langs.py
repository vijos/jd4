import shlex
from appdirs import user_config_dir
from asyncio import gather
from functools import partial
from os import mkfifo, path
from ruamel import yaml

from jd4.compile import Compiler, Interpreter
from jd4.log import logger
from jd4.util import read_pipe

_CONFIG_DIR = user_config_dir('jd4')
_LANGS_FILE = path.join(_CONFIG_DIR, 'langs.yaml')
_MAX_OUTPUT = 8192

async def _compiler_build(compiler, sandbox, code):
    await compiler.prepare(sandbox, code)
    output_file = path.join(sandbox.in_dir, 'output')
    mkfifo(output_file)
    (package, status), output = await gather(
        compiler.build(sandbox, stdout_file='/in/output', stderr_file='/in/output'),
        read_pipe(output_file, _MAX_OUTPUT))
    return package, output.decode(encoding='utf-8', errors='replace')

async def _interpreter_build(interpreter, _, code):
    return interpreter.build(code), None

def _load_langs():
    with open(_LANGS_FILE) as file:
        langs_config = yaml.load(file, Loader=yaml.RoundTripLoader)
    langs = dict()
    for lang_name, lang_config in langs_config.items():
        if lang_config['type'] == 'compiler':
            compiler = Compiler(lang_config['compiler_file'],
                                shlex.split(lang_config['compiler_args']),
                                lang_config['code_file'],
                                lang_config['execute_file'],
                                shlex.split(lang_config['execute_args']))
            langs[lang_name] = partial(_compiler_build, compiler)
        elif lang_config['type'] == 'interpreter':
            interpreter = Interpreter(lang_config['code_file'],
                                      lang_config['execute_file'],
                                      shlex.split(lang_config['execute_args']))
            langs[lang_name] = partial(_interpreter_build, interpreter)
        else:
            logger.error('Unknown type %s', lang_config['type'])
    return langs

langs = _load_langs()

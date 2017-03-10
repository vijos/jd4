import shlex
from appdirs import user_config_dir
from os import path
from ruamel import yaml

from jd4.compile import Compiler, Interpreter
from jd4.log import logger

_CONFIG_DIR = user_config_dir('jd4')
_LANGS_FILE = path.join(_CONFIG_DIR, 'langs.yaml')

def _load_langs():
    with open(_LANGS_FILE) as file:
        langs_config = yaml.load(file, Loader=yaml.RoundTripLoader)
    langs = dict()
    for lang_name, lang_config in langs_config.items():
        if lang_config['type'] == 'compiler':
            langs[lang_name] = Compiler(lang_config['compiler_file'],
                                        shlex.split(lang_config['compiler_args']),
                                        lang_config['code_file'],
                                        lang_config['execute_file'],
                                        shlex.split(lang_config['execute_args'])).build
        elif lang_config['type'] == 'interpreter':
            inner_build = Interpreter(lang_config['code_file'],
                                      lang_config['execute_file'],
                                      shlex.split(lang_config['execute_args'])).build
            async def build(_, code):
                return 0, inner_build(code)
            langs[lang_name] = build
        else:
            logger.error('Unknown type %s', lang_config['type'])
    return langs

langs = _load_langs()

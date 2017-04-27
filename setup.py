from setuptools import setup
from Cython.Build import cythonize

setup(
    name = 'jd4',
    version = '4.0.0',
    description = 'Judging daemon for programming contests',
    url = 'https://github.com/vijos/jd4',
    author = 'iceboy',
    author_email = 'me\x40iceboy.org',
    license = 'AGPL 3',
    packages = ['jd4'],
    install_requires=open('requirements.txt').readlines(),
    ext_modules = cythonize(['jd4/_compare.pyx',
                             'jd4/_sandbox.pyx']),
)

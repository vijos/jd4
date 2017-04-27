from setuptools import setup
from Cython.Build import cythonize

setup(
    install_requires=['cython'],
    ext_modules = cythonize('jd4/_compare.pyx'),
)

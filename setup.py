import sys
from os import path

from setuptools import setup
from setuptools.command.test import test as TestCommand

from socialscan import __version__

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


# https://docs.pytest.org/en/latest/goodpractices.html#manual-integration
class PyTest(TestCommand):
    user_options = [("pytest-args=", "a", "Arguments to pass to pytest")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ""

    def run_tests(self):
        import shlex

        import pytest

        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)


setup(
    name='socialscan',
    version=__version__,
    description='CLI and library for checking email address and username usage on online platforms',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/iojw/socialscan',
    author='Isaac Ong',
    author_email='isaacong.jw@gmail.com',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: AsyncIO',
        'Environment :: Console',
        'Operating System :: OS Independent',
        'Topic :: Utilities',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='email email-checker username username-checker social-media',
    packages=['socialscan'],
    python_requires='>=3.7',
    install_requires=['colorama', 'aiohttp>=3.5.0', 'tqdm>=4.31.0'],
    tests_require=['pytest'],
    cmdclass={"test": PyTest},
    entry_points={
        'console_scripts': [
            'socialscan=socialscan.__main__:main',
        ],
    },
)

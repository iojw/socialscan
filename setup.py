from setuptools import setup
from os import path
from socialscan import __version__

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='socialscan',
    version=__version__,
    description='Accurately check if emails and usernames are in use on social media platforms',
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
    install_requires=['colorama', 'aiohttp', 'tqdm'],
    entry_points={
        'console_scripts': [
            'socialscan=socialscan.__main__:main',
        ],
    },
)

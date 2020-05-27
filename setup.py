from os import path

from setuptools import setup

from socialscan import __version__

here = path.abspath(path.dirname(__file__))

install_requires = [
    'dataclasses;python_version<"3.7"',
    "colorama",
    "aiohttp>=3.5.0",
    "tqdm>=4.31.0",
]

tests_requires = ["tox", "flake8"]

with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="socialscan",
    version=__version__,
    description="Open-source intelligence tool for checking email address and username usage on online platforms",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/iojw/socialscan",
    author="Isaac Ong",
    author_email="isaacong.jw@gmail.com",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: AsyncIO",
        "Environment :: Console",
        "Operating System :: OS Independent",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    keywords="email email-checker username username-checker social-media",
    packages=["socialscan"],
    python_requires=">=3.6",
    install_requires=install_requires,
    extras_require={"tests": install_requires + tests_requires},
    entry_points={"console_scripts": ["socialscan=socialscan.__main__:main"]},
)

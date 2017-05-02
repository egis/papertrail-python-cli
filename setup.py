#!/usr/bin/env python

import os
from setuptools import find_packages, setup

requirements=[
    'Click',
    'requests',
    'progressbar2',
    'termcolor',
    'colorama',
    'watchdog'
]

if os.name == 'posix':
    requirements.append('sh')

setup(
    name='papertrail-cli',
    version='1.0.0',
    install_requires=requirements,
    author='Egis Software',
    url='https://github.com/egis/papertrail-python-cli',
    description='Papertrail Command Line Utils',
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "pt = pt.pt:main",
        ]
    }
)

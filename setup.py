#!/usr/bin/env python

import os
from setuptools import setup

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
    name='pt',
    version='0.3.1',
    install_requires=requirements,
    author='Egis Software',
    url='http://papertrail.co.za',
    description='Papertrail Command Line Utils',
    packages=['pt', 'pt.commands'],
    entry_points='''
    [console_scripts]
    pt=pt.pt:papertrail
    '''
)

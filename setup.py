#!/usr/bin/env python

from setuptools import setup

setup(
    name='pt',
    version='0.3.0',
    install_requires=[
        'Click',
        'requests',
        'progressbar2',
        'sh',
        'termcolor',
        'colorama',
        'watchdog'
    ],
    author='Egis Software',
    url='http://papertrail.co.za',
    description='Papertrail Command Line Utils',
    packages=['pt', 'pt.commands'],
    entry_points='''
    [console_scripts]
    pt=pt.pt:papertrail
    '''
)

from setuptools import setup

setup(
    name='pt',
    version='0.2',
    py_modules=['pt'],
    install_requires=[
        'Click',
        'requests'
    ],
    entry_points='''
    [console_scripts]
    pt=pt:papertrail
    '''
)

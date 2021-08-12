from setuptools import setup

# Read the contents of the README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='PyMetEireann',
    packages=['meteireann'],
    install_requires=['xmltodict', 'aiohttp', 'async_timeout', 'pytz'],
    version='0.3',
    description='A library to communicate with the Met Éireann Public Weather Forecast and Weather Warning APIs',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Dylan Gore',
    author_email='hello@dylangore.ie',
    license='MIT',
    url='https://github.com/DylanGore/PyMetEireann/',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Home Automation',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)

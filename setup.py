from setuptools import setup

setup(
    name='PyMetEireann',
    packages=['meteireann'],
    install_requires=['xmltodict', 'aiohttp', 'async_timeout', 'pytz'],
    version='0.2',
    description='A library to communicate with the Met Éireann Public Weather Forecast API',
    author='Dylan Gore',
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

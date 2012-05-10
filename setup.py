__author__ = 'mm'

from distutils.core import setup

setup(
    name='SizeFS',
    version='0.1.0',
    author='Mark McArdle',
    author_email='m.mc4rdle@gmail.com',
    packages=['sizefs', 'sizefs.test'],
    scripts=[],
    #url='http://pypi.python.org/pypi/SizeFS/',
    license='LICENSE.txt',
    description='SizeFS is a tool for creating files of particular sizes.',
    long_description=open('README.txt').read(),
    install_requires=[
        "fs>=0.4.0",
        ],
)
# -*- coding: utf-8 -*-

# Learn more: https://github.com/kennethreitz/setup.py

from setuptools import setup, find_packages


# with open('README.rst') as f:
#     readme = f.read()

# with open('LICENSE') as f:
#     license = f.read()

setup(
    name='python_bugreport_parser',
    version='0.1.0',
    description='Bugreport Parser',
    long_description="readme",
    author='Me',
    author_email='me',
    url='',
    license="license",
    packages=find_packages(exclude=('tests', 'docs'))
)

#!/usr/bin/env python

from setuptools import setup, find_packages

VERSION = '2022.4.28.1'
DESCRIPTION = 'A Python library used for communicating with the ACEStat.'

setup(
    name="acestatpy",
    version=VERSION,
    author="Jesse M. Barr",
    author_email="Jesse.M.Barr@erdc.dren.mil",
    description=DESCRIPTION,
    long_description=open('README.md').read(),
    python_requires=">=3.6,<4",
    install_requires=[
        "PyDispatcher==2.0.5",
        "pyserial==3.5"
    ],
    packages=find_packages(),
    url="",
    include_package_data=True,
    extras_require={
        'android': [
            'usbserial4a==0.3.0',
            'usb4a==0.2.0'
        ],
    }
)

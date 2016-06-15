#!/usr/bin/env python
# coding=utf-8
import os, sys
from copy import copy

import collections
from setuptools import setup, find_packages

__version__ = open('VERSION','rU').read()
sys.path.insert(0,'nmrbrew')

# Defaults for py2app / cx_Freeze
build_py2app=dict(
    argv_emulation=True,
    includes=[
        'PyQt5',
        "PyQt5.uic.port_v3.proxy_base",

        'nmrglue',
        'nmrglue.fileio.fileiobase',

        ],
    excludes=[
        '_xmlplus',
        'test',
        'networkx',
        'wx',
        'mpl-data',
        'Tkinter',
        "collections.abc",
        'nose',
        'PyQt4',
        'PySide',
        'debug',
        ],  
    resources=[
        'nmrbrew/tools',
        'nmrbrew/icons',
        'nmrbrew/static',
        'nmrbrew/translations',
        'VERSION',
        'README.md',
    ],
    plist=dict(
        CFBundleName = "NMRBrew",
        CFBundleShortVersionString = __version__,
        CFBundleGetInfoString = "NMRBrew %s" % __version__,
        CFBundleExecutable = "NMRBrew",
        CFBundleIdentifier = "org.nmrbrew.nmrbrew",
    ),    
    iconfile='nmrbrew/static/icon.icns',
    #/usr/local/Cellar/qt5/5.3.2/plugins
    qt_plugins=[
        'platforms/libqcocoa.dylib',
        'imageformats',
        'printsupport/libcocoaprintersupport.dylib',
        'accessible',
        ],
    )

setup(

    name='NMRBrew',
    version=__version__,
    author='Martin Fitzpatrick',
    packages = find_packages(),
    include_package_data = True,
    app=['NMRBrew.py'],
    options={
        'py2app': build_py2app,
        },
    setup_requires=['py2app'],
    )

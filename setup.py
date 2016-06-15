#!/usr/bin/env python
# coding=utf-8
import os, sys
from copy import copy

import collections
from setuptools import setup, find_packages

__version__ = open('VERSION','rU').read()
sys.path.insert(0,'nmrbrew')
setup(

    name='NMRBrew',
    version=__version__,
    author='Martin Fitzpatrick',
    author_email='martin.fitzpatrick@gmail.com',
    url='https://github.com/mfitzp/nmrbrew',
    download_url='https://github.com/mfitzp/nmrbrew/zipball/master',
    description='1D NMR spectra processing built on nmrglue.',
    long_description='Interactive 1D NMR spectra processing build on nmrglue',
        
    packages = find_packages(),
    include_package_data = True,
    package_data = {
        '': ['*.txt', '*.rst', '*.md'],
        'plugins':['*'],
    },
    include_files= [
        ('VERSION','VERSION'),
        ('nmrbrew/static', 'static'),
        ('nmrbrew/tools', 'tools'),
        ('nmrbrew/translations', 'translations'),
        ('nmrbrew/icons', 'icons'),
        ],
    
    exclude_package_data = { '': ['README.txt'] },
    entry_points={
        'gui_scripts': [
            'NMRBrew = nmrbrew.NMRBrew:main',
        ]
    },

    install_requires = [
            'PyQt5',
            'sip',
            'numpy>=1.5.0',
            'scipy>=0.14.0',
            'pyqtconfig',
            'nmrglue',
            'pyqtgraph',
            ],


    keywords='bioinformatics data analysis metabolomics research science',
    license='GPL',
    classifiers=['Development Status :: 3 - Alpha',
               'Natural Language :: English',
               'Operating System :: OS Independent',
               'Programming Language :: Python :: 2',
               'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
               'Topic :: Scientific/Engineering :: Bio-Informatics',
               'Topic :: Education',
               'Intended Audience :: Science/Research',
               'Intended Audience :: Education',
              ],

    )
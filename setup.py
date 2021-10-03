#!/usr/bin/env python

from distutils.core import setup

setup(name='buffham',
      version='0.1',
      description='BuffHam Encoding Utilities',
      author='Ryan Draves',
      author_email='dravesr@umich.edu',
      packages=['buffham'],
      scripts=[
          'buffham/buffham_gen.py'
      ]
     )
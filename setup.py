#!/usr/bin/env python

from distutils.core import setup

setup(name='mailinglistbot',
      version='0.3',
      description='Python telegram bot to mirror a group in a mailinglist',
      author='Leonardo Maccari',
      author_email='mail@leonardo.ma',
      py_modules=['mailinglistbot', 'db', 'apitoken'],
     )

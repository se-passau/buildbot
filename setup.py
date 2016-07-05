#!/usr/bin/env python2
from setuptools import setup, find_packages
setup(name='benchbuild.buildbot',
      version='0.1',
      url='https://github.com/PolyJIT/buildbot',
      packages=[
          'benchbuild', 'benchbuild.buildbot', 'benchbuild.buildbot.builders'
      ],
      install_requires=["buildbot>=0.8.9"],
      author="Andreas Simbuerger",
      author_email="simbuerg@fim.uni-passau.de",
      description="Buildbot drivers.",
      license="MIT",
      classifiers=[
          'Development Status :: 4 - Beta', 'Intended Audience :: Developers',
          'Topic :: Software Development :: Testing',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3'
      ],
      keywords="benchbuild buildbot", )

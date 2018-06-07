#!/usr/bin/env python2
from setuptools import setup, find_packages
setup(name='polyjit.buildbot',
      version='0.1',
      url='https://github.com/PolyJIT/buildbot',
      packages=find_packages(),
      install_requires=["buildbot>=0.9.7",
                        "buildbot-console-view",
                        "buildbot-waterfall-view",
                        "buildbot-www",
                        "treq"],
      author="Andreas Simbuerger",
      author_email="simbuerg@fim.uni-passau.de",
      description="Buildbot drivers.",
      license="MIT",
      classifiers=[
          'Development Status :: 4 - Beta', 'Intended Audience :: Developers',
          'Topic :: Software Development :: Testing',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 2'
      ],
      keywords="polyjit buildbot", )

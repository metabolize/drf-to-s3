# https://coderwall.com/p/qawuyq
# Thanks James.

try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except (IOError, ImportError):
    long_description = ''
    print 'warning: pandoc or pypandoc does not seem to be installed; using empty long_description'

import os
requirements_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'requirements.txt')
with open(requirements_file, 'r') as f:
    install_requires = [x.strip() for x in f.readlines()]

from setuptools import setup

setup(
    name = 'drf_to_s3',
    version = __import__('drf_to_s3').__version__,
    author = 'Body Labs',
    author_email = 'paul.melnikow@bodylabs.com',
    description = 'Django REST Framework Interface for direct upload to S3',
    long_description = long_description,
    url = 'https://github.com/bodylabs/drf-to-s3',
    license = 'MIT',
    packages = [
        'drf_to_s3',
    ],
    install_requires=install_requires,
    classifiers = [
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP'
    ]
)

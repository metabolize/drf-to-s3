# https://coderwall.com/p/qawuyq
# Thanks James.

try:
   import pypandoc
   long_description = pypandoc.convert('README.md', 'rst')
except (IOError, ImportError):
   long_description = ''

from setuptools import setup

setup(
    name = 'drf_to_s3',
    version = __import__('drf_to_s3').__version__,
    author = 'Body Labs',
    author_email = 'paul.melnikow@bodylabs.com',
    description = 'Django REST Framework Interface for direct upload to S3',
    long_description = long_description,
    url = 'https://bitbucket.org/bodylabs/drf-to-s3',
    license = 'All rights reserved',
    packages = [
        'drf_to_s3',
    ],
    classifiers = [
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: Other/Proprietary License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP'
    ]
)

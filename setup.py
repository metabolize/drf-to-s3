# https://coderwall.com/p/qawuyq
# Thanks James.

try:
   import pypandoc
   long_description = pypandoc.convert('README.md', 'rst')
except (IOError, ImportError):
   long_description = ''

from setuptools import setup

setup(
    name = 's3_upload',
    version = __import__('s3_upload').__version__,
    author = 'Body Labs',
    author_email = 'paul.melnikow@bodylabs.com',
    description = 'Django REST Framework Interface for direct upload to S3',
    long_description = long_description
    url = 'https://bitbucket.org/bodylabs/drf-to-s3',
    license = 'All rights reserved',
    packages = [
        's3_upload',
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

# https://coderwall.com/p/qawuyq
# Thanks James.

try:
   import pypandoc
   long_description = pypandoc.convert('README.md', 'rst')
except (IOError, ImportError):
   long_description = ''

from setuptools import setup

setup(
    name = "drf-to-s3",
    version = __import__("passwords").__version__,
    author = "Body Labs",
    author_email = "paul.melnikow@bodylabs.com",
    description = "Django REST Framework interface for direct upload to S3",
    long_description = long_description
    url = "http://github.com/dstufft/django-passwords/",
    license = "BSD",
    packages = [
        "passwords",
    ],
    classifiers = [
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Utilities",
        "Framework :: Django",
    ]
)

drf-to-s3
=========

[Django REST Framework][] interface for direct upload to S3.
Designed for browser-based clients using [Fine Uploader][]
and API clients.


Features
--------

### Handles browser-based uploads ###

 1. Signs [policy documents][] for the [POST API][].
 2. Provides an empty response to use as a success action
    redirect with old browsers (IE 9 and Android 2.3.x) which
    do not support the File API, instead using a dynamically
    generated iframe.
 3. Provides a framework for your upload-complete callback,
    which should copy the file to storage and take whatever
    other action is needed, such as creating model objects.

See this [Fine Uploader blog post][] for a long explanation
of these responsibilities.

### Handles API-client uploads ###

The library provides a streamlined interface suitable for
programmatic uploads by non-browser-based API clients:

 1. Provides signed URIs for the [REST PUT Object API][].
 2. Provides an upload-complete callback.


Designed for security
---------------------

This library's design goal is to be secure by default. To
that end, it makes two recommendations:

 1. Send your uploads to an "uploads" bucket, and make them
    private. This simplifies the namespacing used to
    segregate uploads by user, and discourages read-write
    ACLs.
 2. Create an account which has the minimum permission
    required on your uploads bucket, and use that account
    to sign users' policy documents.
 3. Move the files into a storage bucket during the
    completion callback, with either private or read-only
    ACLs. The library provides a view and serializer you
    can subclass to accomplish this easily.
 4. Use Fine Uploader's
    [`objectProperties.key`][objectProperties.key] property
    to incorporate the username as a prefix in the key. If
    you don't already have access to the username in the
    client, you can use the library's middleware to set a
    cookie with the prefix.
 5. Be sure to specify an `https` endpoint url when you
    configure Fine Uploader.
 6. Set a one-day expiration policy which automatically
    deletes stale, incomplete uploads. This step is mainly
    to save you money.

If you're willing to take what hopefully is
sensible-sounding advice, go on to the next section. If you
want to know *why*, see the discussion in SECURITY.md.

If you don't want to use it as designed, you can use the
utility classes and naive serializers to create your own
components.


Status
------

This project is functional pre-alpha. Most significantly it needs
better documentation.

[![Build Status](https://travis-ci.org/bodylabs/drf-to-s3.png?branch=master)](https://travis-ci.org/bodylabs/drf-to-s3)


Installation
------------

Requires [Django REST Framework][], a great toolkit for building
Web APIs in Django.

        pip install drf_to_s3

This will install the remaining dependencies: [boto][],
and [querystring_parser][] which handles nested keys within
`uploadSuccess.params`.

Temporarily, you must use our fork of querystring_parser. Please
install it separately:

        -e git+https://github.com/bodylabs/querystring-parser@patched#egg=querystring_parser


How to use
----------

 1. Include `drf_to_s3.urls` in your site (or if you prefer,
    redefine them).
 2. If you want to use nested dictionaries in your success
    callback, you must disable Django REST Framework's
    options for overriding the HTTP method and content.
    You probably aren't using these options, and they
    [interfere with the view's use of a custom form parser][issue].

        REST_FRAMEWORK = {    
            'FORM_METHOD_OVERRIDE': None,
            'FORM_CONTENT_OVERRIDE': None,
        }

 3. Create an temporary bucket for uploads.
 4. Set the CORS policy on that bucket.
 5. Create a user which only has PutObject access to that
    bucket.
 6. Add Fine Uploader to your front end.
 7. Configure Fine Uploader:

      - Keys
      - `request.key`
      - access key


Limitations
-----------

Users must be logged in to upload. Anonymous uploads
currently aren't supported.

Deletes during upload are not supported, but would be easy
to add.


Contributing
------------

- Issue Tracker: https://github.com/bodylabs/drf-to-s3/issues
- Source Code: https://github.com/bodylabs/drf-to-s3

### Unit tests: ###

    rake create_venv
    . .venv/bin/activate
    rake install
    rake test

### Unit tests against S3: ###

  1. If it's not already installed on your system, install
     `foreman`. You can get it from RubyGems with
     `gem install foreman` or install [Heroku Toolbelt][].
  2. Create an S3 bucket to use for testing.
  3. Create a `.env` file at the project root with the
     following three lines:

       - AWS_TEST_BUCKET=...
       - AWS_ACCESS_KEY_ID=...
       - AWS_SECRET_ACCESS_KEY=...

  4. Run the tests:

        source venv/bin/activate
        foreman run drf_to_s3/runtests/runtests.py

### Integration tests: ###

  1. Install `foreman`, create an S3 bucket, and set up your
     `.env` file as described above.

  2. Install Node, NPM, the build dependences for
     Fine Uploader, and Chromium Driver:

        rake install_integration

  3. If you're not using Mac OS / Homebrew, you need to install
     Chromium Driver some other way.

  4. Choose a version of Fine Uploader to test:

        rake install_fine

  5. Build it into `drf_to_s3/integration/static`:

        rake install_fine[4.2.2]

  6. Run the tests

        rake integration

### Running integration tests on Sauce Labs: ###

  1. Create a [Sauce Labs][] account.
  2. In .env, set `SAUCE_USERNAME` and `SAUCE_ACCESS_KEY`.
  3. Install [Sauce Connect][].
  4. Start Sauce Connect:

      foreman run sh -c 'java -jar ~/code/Sauce-Connect-latest/Sauce-Connect.jar $SAUCE_USERNAME $SAUCE_ACCESS_KEY'

  5. Run the tests:

      WITH_SAUCE=1 rake integration

### Building the package for PyPi: ###

This readme is written in Markdown, so there are
dependencies for converting it to reStructuredText.
You only need this if you want to generate the PyPi
package with long_description intact. Without it,
you'll just get a warning.

    rake install_dist

If you're not using MacOS / Homebrew, you'll need to
install Pandoc some other way.

License
-------

This project is licensed under the MIT license.


[Django REST Framework]: http://django-rest-framework.org/
[Fine Uploader]: http://fineuploader.com/
[POST API]: http://docs.aws.amazon.com/AmazonS3/latest/dev/HTTPPOSTForms.html
[REST PUT Object API]: http://docs.aws.amazon.com/AmazonS3/latest/API/RESTObjectPUT.html
[policy documents]: http://docs.aws.amazon.com/AmazonS3/latest/dev/HTTPPOSTForms.html#HTTPPOSTConstructPolicy
[Fine Uploader blog post]: http://blog.fineuploader.com/2013/08/16/fine-uploader-s3-upload-directly-to-amazon-s3-from-your-browser/
[boto]: https://github.com/boto/boto
[querystring_parser]: https://github.com/bernii/querystring-parser
[issue]: https://github.com/tomchristie/django-rest-framework/issues/1346
[Heroku Toolbelt]: https://toolbelt.heroku.com/
[Sauce Labs]: https://saucelabs.com/
[Sauce Connect]: http://saucelabs.com/downloads/Sauce-Connect-latest.zip
[objectProperties.key]: http://docs.fineuploader.com/api/options-s3.html#objectProperties.key

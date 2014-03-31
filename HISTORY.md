drf-to-s3 Release History
=========================

0.7.5
-----
March 31, 2014

Install querystring_parser dependency from PyPI.


0.7.4
-----
March 27, 2014

Fix validation of x-amz-meta-qqfilename, which is not the filename but
rather the the URL-encoded filename.


0.7.3
-----
March 26, 2014

A more correct fix to NestedFormParser for non-ascii characters.

Depends on our fork of querystring_parser:

-e git+https://github.com/bodylabs/querystring-parser@patched#egg=querystring_parser


0.7.2
-----
March 14, 2014

Fix NestedFormParser to properly handle non-ascii characters.


0.7.1
-----
February 10, 2014

Fix for pip install.


0.7
---
February 10, 2014

Add separate views and serializers for API-client uploads. Views
are now in `drf_to_s3.views.fine_uplaoder_views` and
`drf_to_s3.views.api_client_views`.


0.6.1
-----
February 1, 2014

Initial public release.

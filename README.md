drf-to-s3
=========

Interface for direct upload to S3 using the [POST API][].

Designed for use with the excellent [Fine Uploader][]
using the excellent [Django REST Framework][].

This service has a few essential responsibilities:

 1. Sign [policy documents][]
 2. Provide an empty response to use as a success action redirect
    with old browsers (IE 9 and Android 2.3.x) which do not support
    the File API, instead using a dynamically generated iframe
 3. Provide an upload-complete callback

See this [Fine Uploader blog post][] for a long explanation of
these responsibilities.

[Django REST Framework]: http://django-rest-framework.org/
[Fine Uploader]: http://fineuploader.com/
[POST API]: http://docs.aws.amazon.com/AmazonS3/latest/dev/HTTPPOSTForms.html
[policy documents]: http://docs.aws.amazon.com/AmazonS3/latest/dev/HTTPPOSTForms.html#HTTPPOSTConstructPolicy
[Fine Uploader blog post]: http://blog.fineuploader.com/2013/08/16/fine-uploader-s3-upload-directly-to-amazon-s3-from-your-browser/

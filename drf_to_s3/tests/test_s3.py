import os
import unittest, uuid
from django.test.utils import override_settings

class S3Test(unittest.TestCase):
    prefix = 'drf-to-s3/'

    def setUp(self):
        import boto
        from boto.exception import NoAuthHandlerFound
        from boto.s3.key import Key

        keys = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']
        try:
            for k in keys:
                os.environ[k]
            self.bucket_name = os.environ.get('AWS_TEST_BUCKET', 'drf-to-s3-test')
        except KeyError:
            self.skipTest('To test s3, set %s in .env' % ' and '.join(keys))

        conn = boto.connect_s3()
        bucket = conn.get_bucket(self.bucket_name)
        k = Key(bucket)
        k.key = "%s%s.txt" % (str(uuid.uuid4()), self.prefix)
        k.set_contents_from_string('This is a test of S3')

        self.existing_key = k.key
        self.existing_key_etag = k.etag
        self.bucket = bucket

        self.nonexisting_key = "%s%s.txt" % (str(uuid.uuid4()), self.prefix)
        self.new_key = None

    def tearDown(self):
        import boto
        conn = boto.connect_s3()
        self.bucket.delete_key(self.existing_key)
        self.bucket.delete_key(self.nonexisting_key)
        if self.new_key:
            self.bucket.delete_key(self.new_key)

    def test_can_put_to_generated_signed_url(self):
        import os, tempfile, requests, uuid
        from drf_to_s3 import s3
        from django.conf import settings

        self.new_key = '%s/%s' % ('nobody@bodylabs.com', str(uuid.uuid4()))
        aws_access_id = os.environ['AWS_ACCESS_KEY_ID']
        secret_key = os.environ['AWS_SECRET_ACCESS_KEY']

        signed_url = s3.build_signed_upload_uri(
            bucket=self.bucket_name,
            key=self.new_key,
            access_key_id=aws_access_id,
            secret_key=secret_key,
            expire_after_seconds=60
        )

        with tempfile.NamedTemporaryFile() as f:
            f.write(os.urandom(1024))
            resp = requests.put(signed_url, data=f.read())
            self.assertEquals(resp.status_code, 200)

    def test_copy_succeeds(self):
        from drf_to_s3 import s3
        s3.copy(
            src_bucket=self.bucket_name,
            src_key=self.existing_key,
            dst_bucket=self.bucket,
            dst_key=self.nonexisting_key,
            src_etag=self.existing_key_etag,
            validate_src_etag=True
        )

    def test_copy_fails_with_mismatched_etag_after_subsequent_update(self):
        from boto.s3.key import Key
        from drf_to_s3 import s3

        k = Key(self.bucket)
        k.key = self.existing_key
        k.set_contents_from_string('Another test')

        with self.assertRaises(s3.ObjectNotFoundException):
            s3.copy(
                src_bucket=self.bucket_name,
                src_key=self.existing_key,
                dst_bucket=self.bucket_name,
                dst_key=self.nonexisting_key,
                src_etag=self.existing_key_etag,
                validate_src_etag=True
            )

    def test_copy_succeeds_without_etag_validation_after_subsequent_update(self):
        from boto.s3.key import Key
        from drf_to_s3 import s3

        k = Key(self.bucket)
        k.key = self.existing_key
        k.set_contents_from_string('Another test')

        s3.copy(
            src_bucket=self.bucket_name,
            src_key=self.existing_key,
            dst_bucket=self.bucket_name,
            dst_key=self.nonexisting_key
        )

    def test_copy_fails_on_nonexistent_key(self):
        from drf_to_s3 import s3
        another_nonexisting_key = str(uuid.uuid4()) + '.txt'
        with self.assertRaises(s3.ObjectNotFoundException):
            s3.copy(
                src_bucket=self.bucket_name,
                src_key=another_nonexisting_key,
                dst_bucket=self.bucket_name,
                dst_key=self.nonexisting_key,
                src_etag=self.existing_key_etag,
                validate_src_etag=True
            )

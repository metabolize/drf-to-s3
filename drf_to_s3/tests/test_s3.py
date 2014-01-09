import unittest, uuid

class S3Test(unittest.TestCase):
    prefix = 'drf-to-s3/'
    bucket_name = 'bodylabs-test'

    def setUp(self):
        import boto
        from boto.s3.key import Key

        conn = boto.connect_s3()
        bucket = conn.get_bucket(self.bucket_name)
        k = Key(bucket)
        k.key = "%s%s.txt" % (str(uuid.uuid4()), self.prefix)
        k.set_contents_from_string('This is a test of S3')

        self.existing_key = k.key
        self.existing_key_etag = k.etag
        self.bucket = bucket

        self.nonexisting_key = "%s%s.txt" % (str(uuid.uuid4()), self.prefix)

    def tearDown(self):
        import boto
        conn = boto.connect_s3()
        self.bucket.delete_key(self.existing_key)
        self.bucket.delete_key(self.nonexisting_key)

    def test_copy_succeeds(self):
        from drf_to_s3 import s3
        new_key = str(uuid.uuid4()) + '.txt'
        s3.copy(
            src_bucket=self.bucket_name,
            src_key=self.existing_key,
            etag=self.existing_key_etag,
            dst_bucket=self.bucket,
            dst_key=self.nonexisting_key
        )

    def test_copy_fails_after_subsequent_update(self):
        from boto.s3.key import Key
        from drf_to_s3 import s3

        k = Key(self.bucket)
        k.key = self.existing_key
        k.set_contents_from_string('Another test')

        new_key = str(uuid.uuid4()) + '.txt'
        with self.assertRaises(s3.ObjectNotFoundException):
            s3.copy(
                src_bucket=self.bucket_name,
                src_key=self.existing_key,
                etag=self.existing_key_etag,
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
                etag=self.existing_key_etag,
                dst_bucket=self.bucket_name,
                dst_key=self.nonexisting_key
            )

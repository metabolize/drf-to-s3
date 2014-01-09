from rest_framework import status
from rest_framework.exceptions import APIException

def sign_policy_document(policy_document, secret_key):
    '''
    Sign the given policy document.

    Returns a dictionary with the policy and the signature.

    http://aws.amazon.com/articles/1434/#signyours3postform
    '''
    import base64, json, hmac, hashlib
    policy = base64.b64encode(json.dumps(policy_document))
    signature = base64.b64encode(hmac.new(secret_key, policy, hashlib.sha1).digest())
    return {
        'policy': policy,
        'signature': signature,
    }

def utc_plus(seconds):
    import datetime
    return datetime.datetime.utcnow() + datetime.timedelta(0, seconds)

def validate_bucket_name(string_value):
    '''
    Validate the bucket name. These rules are for the US Standard
    region which are more lenient than others.

    http://docs.aws.amazon.com/AmazonS3/latest/dev/BucketRestrictions.html
    '''
    import string
    if len(string_value) < 3 or len(string_value) > 255:
        return False
    allowed_characters = "-._" + string.ascii_letters + string.digits
    return all([char in allowed_characters for char in string_value])


class ObjectNotFoundException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = 'Invalid key or bad ETag'


def copy(src_bucket, src_key, etag, dst_bucket, dst_key):
    '''
    Copy a key, with a given etag, from one bucket to another.

    Raises ObjectNotFoundException if the key does not exist
    or the ETag doesn't match.

    We return the same error in either case, since a mismatched
    ETag might mean the user wasn't the last to upload the object.
    If the bucket is private they may not even know it exists.
    By returning the same error, we avoid giving out extra
    information.

    '''
    import boto
    from boto.exception import S3ResponseError
    conn = boto.connect_s3()
    bucket = conn.get_bucket(dst_bucket)
    try:
        bucket.copy_key(
            new_key_name=dst_key,
            src_bucket_name=src_bucket,
            src_key_name=src_key,
            headers={'x-amz-copy-source-if-match': etag}
        )
    except S3ResponseError as e:
        if e.status in [status.HTTP_404_NOT_FOUND, status.HTTP_412_PRECONDITION_FAILED]:
            raise ObjectNotFoundException()
        else:
            raise

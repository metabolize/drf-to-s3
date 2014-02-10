from rest_framework import status
from rest_framework.exceptions import APIException
from django.utils.translation import ugettext as _


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

def sign_rest_request(secret_key, method, content_md5='', content_type='', expires='', canonicalized_headers='', canonicalized_resource=''):
    '''
    Construct a signature suitable for a REST request.

    http://docs.aws.amazon.com/AmazonS3/latest/dev/RESTAuthentication.html#RESTAuthenticationExamples

    '''
    import base64, hashlib, hmac
    string_to_sign = "\n".join([method, content_md5, content_type, str(expires), canonicalized_headers, canonicalized_resource])
    return base64.b64encode(hmac.new(secret_key, string_to_sign, hashlib.sha1).digest())

def build_signed_upload_uri(bucket, key, access_key_id, secret_key, expire_after_seconds):
    '''
    Accept bucket name, bucket key and s3 credentials as input
    Return signed_url for PUT upload.
    
    http://docs.aws.amazon.com/AmazonS3/latest/dev/RESTAuthentication.html#RESTAuthenticationExamples
    '''

    import numbers, time, base64, hmac, urllib, hashlib
    for v in [bucket, key, access_key_id, secret_key]:
        if not isinstance(v, basestring) or not len(v):
            raise ValueError('Parameter must be a non-zero-length string')
    if not isinstance(expire_after_seconds, numbers.Integral):
        raise ValueError('expire_after_seconds must be an integer')

    expires = utc_plus_as_timestamp(expire_after_seconds)
    signature = sign_rest_request(
        secret_key,
        method='PUT',
        expires=expires,
        canonicalized_headers='x-amz-acl:private',
        canonicalized_resource=urllib.quote("/%s/%s" % (bucket, key))
    )
    params = {
        'AWSAccessKeyId': access_key_id,
        'Expires': expires,
        'x-amz-acl': 'private',
        'Signature': signature.strip(),
    }
    return 'https://%s.s3.amazonaws.com/%s?%s' % (
        bucket,
        urllib.quote(key),
        urllib.urlencode(params)
    )

def utc_plus(seconds):
    import datetime
    return datetime.datetime.utcnow() + datetime.timedelta(0, seconds)

def utc_plus_as_timestamp(seconds):
    import calendar
    return calendar.timegm(utc_plus(seconds).timetuple())

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
    default_detail = _('Invalid key or bad ETag')


def copy(src_bucket, src_key, dst_bucket, dst_key, src_etag=None, validate_src_etag=False):
    '''
    Copy a key from one bucket to another.

    If validate_etag is True, the ETag must match. Raises
    ObjectNotFoundException if the key does not exist,
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
    if validate_src_etag:
        headers = {
            'x-amz-copy-source-if-match': src_etag,
        }
    else:
        headers = {}
    try:
        bucket.copy_key(
            new_key_name=dst_key,
            src_bucket_name=src_bucket,
            src_key_name=src_key,
            headers=headers
        )
    except S3ResponseError as e:
        if e.status in [status.HTTP_404_NOT_FOUND, status.HTTP_412_PRECONDITION_FAILED]:
            raise ObjectNotFoundException()
        else:
            raise

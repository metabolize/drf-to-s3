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

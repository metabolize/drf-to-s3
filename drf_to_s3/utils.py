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

class UploadPolicy(object):
    '''
    Encapsulates a policy document for an S3 POST request.

    http://docs.aws.amazon.com/AmazonS3/latest/dev/HTTPPOSTForms.html#HTTPPOSTConstructPolicy

    expiration: The policy expiration date, a native datetime.datetime object
    conditions: A list of UploadPolicyCondition objects
    '''
    expiration = None
    conditions = None

    def __init__(self, **kwargs):
        self.expiration = kwargs.get('expiration')
        self.conditions = kwargs.get('conditions')


class UploadPolicyCondition(object):
    '''
    Encapsulates a condition on an UploadPolicy.

    operator: The operator, which is optional. Either 'eq', 'starts-with', or None.
    key: The 
    '''
    # Either 
    operator = None
    element_name = None
    value = None
    value_range = None

    def __init__(self, **kwargs):
        self.operator = kwargs.get('operator')
        self.element_name = kwargs.get('element_name')
        self.value = kwargs.get('value')
        self.value_range = kwargs.get('value_range')



class UploadPolicy(object):
    expiration = None
    conditions = None

    def __init__(self, **kwargs):
        self.expiration = kwargs.get('expiration')
        self.conditions = kwargs.get('conditions')


class UploadPolicyCondition(object):
    operator = None
    key = None
    value = None
    value_range = None

    def __init__(self, **kwargs):
        self.operator = kwargs.get('operator')
        self.key = kwargs.get('key')
        self.value = kwargs.get('value')
        self.value_range = kwargs.get('value_range')

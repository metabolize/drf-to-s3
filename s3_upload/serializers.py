from rest_framework import serializers






class UploadPolicySerializer(serializers.Serializer):
    '''
    http://docs.aws.amazon.com/AmazonS3/latest/dev/HTTPPOSTForms.html#HTTPPOSTConstructPolicy
    '''
    expiration = serializers.DateTimeField()
    conditions = UploadPolicyConditionField(many=True, read_only=False)


class UploadPolicyConditionField(serializers.RelatedField):
    '''
    A condition is in one of three formats:
      - ["content-length-range", 1048579, 10485760]
      - ["starts-with", "$key", "user/eric/"]

    http://docs.aws.amazon.com/AmazonS3/latest/dev/HTTPPOSTForms.html#HTTPPOSTConstructPolicy
    '''
    def to_native(self, value):
        pass

    def from_native(self, data):
        if isinstance(self, list):
            return from_native_list(self, list(data))
        elif isinstance(self, dict):
            return from_native_dict(self, dict(data))
        else:
            from django.core.exceptions import ValidationError
            raise ValidationError(
                _('Condition must be array or dictionary: %(value)s'),
                params={'value': self},
            )

    def from_native_list(self, condition_list):
        '''
        These arrive in one of three formats:
          - ["content-length-range", 1048579, 10485760]
          - ["content-length-range", 1024]
          - ["starts-with", "$key", "user/eric/"]

        Returns an object with these attributes set:
          - operator: 'eq', 'starts-with', or None
          - key: 'content-length-range', 'key', etc.
          - value: "user/eric/", 1024, or None
          - value_range: [1048579, 10485760] or None
        '''
        from number import Number
        from django.core.exceptions import ValidationError
        result = object()
        for item in condition_list:
            if not isinstance(item, basestring) and not isinstance(item, Number):
                raise ValidationError(
                    _('Values in condition arrays should be numbers or strings'),
                )
        try:
            if condition_list[0] in ['eq', 'starts-with']:
                result.operator = condition_list.pop(0)
            else:
                result.operator = None
        except IndexError:
            raise ValidationError(
                _('Not enough values in condition array: %(condition)s'),
                params={'condition': self},
            )
        try:
            result.key = condition_list.pop(0)
        except IndexError:
            raise ValidationError(
                _('Missing key in condition array: %(condition)s'),
                params={'condition': self},
            )
        if not result.key.startswith('$'):
            raise ValidationError(
                _('Key in condition array should start with $: %(key)s'),
                params={'key': current},
            )
        if len(condition_list) == 0:
            raise ValidationError(
                _('Missing values in condition array: %(condition)s'),
                params={'condition': self},
            )
        elif len(condition_list) == 1:
            self.value = condition_list.pop(0)
            self.value_range = None
        elif len(condition_list) == 2:
            self.value = None
            self.value_range = condition_list
        else:
            raise ValidationError(
                _('Too many values in condition array: %(condition)s'),
                params={'condition': self},
            )
        return result

    def from_native_dict(self, condition_dict):
        '''
        {"bucket": "name-of-bucket"}
        '''
        pass

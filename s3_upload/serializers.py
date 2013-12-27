from rest_framework import serializers
from django.utils.translation import ugettext as _


class UploadPolicyConditionField(serializers.RelatedField):
    '''
    The serializer field is responsible for deserializing
    from arrays and dictionaries to UploadPolicyCondition
    objects, and vice versa.

    Though this raises ValidationError for malformed arrays
    and dictionaries, it only validates the structure of
    the representation, not its content. Content is
    validated by the BaseUploadPolicySerializer subclass.

    A condition is in one of three formats:
      - ["content-length-range", 1048579, 10485760]
      - ["starts-with", "$key", "user/eric/"]

    http://docs.aws.amazon.com/AmazonS3/latest/dev/HTTPPOSTForms.html#HTTPPOSTConstructPolicy
    '''
    def to_native(self, value):
        pass

    def from_native(self, data):
        if isinstance(data, list):
            return self.from_native_list(data)
        elif isinstance(data, dict):
            return self.from_native_dict(data)
        else:
            from django.core.exceptions import ValidationError
            raise ValidationError(
                _('Condition must be array or dictionary: %(condition)s'),
                params={'condition': data},
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
        from numbers import Number
        from django.core.exceptions import ValidationError
        from s3_upload.models import UploadPolicyCondition
        original_condition_list = condition_list # We use this for error reporting
        condition_list = list(condition_list)
        for item in condition_list:
            if not isinstance(item, basestring) and not isinstance(item, Number):
                raise ValidationError(
                    _('Values in condition arrays should be numbers or strings'),
                )
        try:
            if condition_list[0] in ['eq', 'starts-with']:
                operator = condition_list.pop(0)
            else:
                operator = None
        except IndexError:
            raise ValidationError(
                _('Empty condition array: %(condition)s'),
                params={'condition': original_condition_list},
            )
        try:
            key = condition_list.pop(0)
        except IndexError:
            raise ValidationError(
                _('Missing key in condition array: %(condition)s'),
                params={'condition': original_condition_list},
            )
        if operator:
            if key.startswith('$'):
                key = key[1:]
            else:
                raise ValidationError(
                    _('Key in condition array should start with $: %(key)s'),
                    params={'key': key},
                )
        if len(condition_list) == 0:
            raise ValidationError(
                _('Missing values in condition array: %(condition)s'),
                params={'condition': original_condition_list},
            )
        elif len(condition_list) == 1:
            value = condition_list.pop(0)
            value_range = None
        elif len(condition_list) == 2:
            value = None
            value_range = condition_list
        else:
            raise ValidationError(
                _('Too many values in condition array: %(condition)s'),
                params={'condition': original_condition_list},
            )
        return UploadPolicyCondition(
            operator=operator,
            key=key,
            value=value,
            value_range=value_range
        )

    def from_native_dict(self, condition_dict):
        '''
        {"bucket": "name-of-bucket"}
        '''
        from numbers import Number
        from django.core.exceptions import ValidationError
        from s3_upload.models import UploadPolicyCondition
        if len(condition_dict) > 1:
            raise ValidationError(
                _('Too many values in condition dictionary: %(condition)s'),
                params={'condition': condition_dict},
            )
        key, value = condition_dict.popitem()
        if not isinstance(value, basestring) and not isinstance(value, Number):
            raise ValidationError(
                _('Values in condition dictionaries should be numbers or strings'),
            )
        return UploadPolicyCondition(
            operator=None,
            key=key,
            value=value,
            value_range=None
        )


class BaseUploadPolicySerializer(serializers.Serializer):
    '''
    http://docs.aws.amazon.com/AmazonS3/latest/dev/HTTPPOSTForms.html#HTTPPOSTConstructPolicy
    '''
    from django.db.models.query import EmptyQuerySet
    expiration = serializers.DateTimeField(required=False)
    conditions = UploadPolicyConditionField(
        many=True,
        read_only=False,
        required=False,
        queryset=EmptyQuerySet
    )


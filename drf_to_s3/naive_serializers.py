from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _


class NaivePolicyConditionField(serializers.RelatedField):
    '''
    Serializes a PolicyCondition instance to a list
    or dictionary, and vice versa.

    It doesn't know about the schema, only about the array
    and dictionary representations. Accordingly, it raises
    ValidationError for malformed arrays and dictionaries,
    but NaiveUploadPolicySerializer is responsible for
    checking that, for example, that values for
    content-length-range are numeric, that element names
    are in the schema, and that required elements like
    'bucket' are present.

    A condition is in one of three formats:
      - ["content-length-range", 1048579, 10485760]
      - ["starts-with", "$key", "user/eric/"]

    http://docs.aws.amazon.com/AmazonS3/latest/dev/HTTPPOSTForms.html#HTTPPOSTConstructPolicy
    '''
    def to_native(self, value):
        if value.value_range is not None:
            if value.value is not None:
                raise ValidationError(
                    _('Do not use value and value_range together')
                )
            if value.operator is not None:
                raise ValidationError(
                    _('operator should not be used with value_range')
                )
            if not isinstance(value.value_range, list):
                raise ValidationError(
                    _('value_range should be a list')
                )
        if value.value_range:
            return [value.element_name] + value.value_range
        elif value.operator:
            return [value.operator, '$' + value.element_name, value.value]
        else:
            return {value.element_name: value.value}

    def from_native(self, data):
        if isinstance(data, list):
            return self._from_native_list(data)
        elif isinstance(data, dict):
            return self._from_native_dict(data)
        else:
            raise ValidationError(
                _('Condition must be array or dictionary, not %(type)s: %(condition)s'),
                params={'type': data.__class__.__name__, 'condition': data},
            )

    def _from_native_list(self, condition_list):
        '''
        These arrive in one of three formats:
          - ["content-length-range", 1048579, 10485760]
          - ["content-length-range", 1024]
          - ["starts-with", "$key", "user/eric/"]

        Returns an object with these attributes set:
          - operator: 'eq', 'starts-with', or None
          - element_name: 'content-length-range', 'key', etc.
          - value: "user/eric/", 1024, or None
          - value_range: [1048579, 10485760] or None
        '''
        from numbers import Number
        from drf_to_s3.models import PolicyCondition
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
            element_name = condition_list.pop(0)
        except IndexError:
            raise ValidationError(
                _('Missing element in condition array: %(condition)s'),
                params={'condition': original_condition_list},
            )
        if operator:
            if element_name.startswith('$'):
                element_name = element_name[1:]
            else:
                raise ValidationError(
                    _('Element name in condition array should start with $: %(element_name)s'),
                    params={'element_name': element_name},
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
        return PolicyCondition(
            operator=operator,
            element_name=element_name,
            value=value,
            value_range=value_range
        )

    def _from_native_dict(self, condition_dict):
        '''
        {"bucket": "name-of-bucket"}
        '''
        from numbers import Number
        from drf_to_s3.models import PolicyCondition
        if len(condition_dict) > 1:
            raise ValidationError(
                _('Too many values in condition dictionary: %(condition)s'),
                params={'condition': condition_dict},
            )
        element_name, value = condition_dict.popitem()
        if not isinstance(value, basestring) and not isinstance(value, Number):
            raise ValidationError(
                _('Values in condition dictionaries should be numbers or strings'),
            )
        return PolicyCondition(
            operator=None,
            element_name=element_name,
            value=value,
            value_range=None
        )


class NaivePolicySerializer(serializers.Serializer):
    '''
    Serializes an UploadPolicy instance to a dictionary, and
    vice versa.

    This class aims to do two things:

     1. Provide configurable validation of essentials like
        bucket and acl
     2. Provide stupid validation of variable types, that
        key and content-type are valid, and so on

    serializer.DefaultPolicySerializer provides more
    conservative defaults.

    To provide custom validation of an individual element, a
    subclass may implement

       def validate_condition_<name>(self, condition):

    which this method automatically will call whenever a condition
    is present with the given element name. Raise a ValidationError
    to indicate an error. Note this method is only called when
    a condition is present. To make the condition required, add
    it to required_conditions.

    '''
    from django.db.models.query import EmptyQuerySet
    expiration = serializers.DateTimeField(required=False, format='%Y-%m-%dT%H:%M:%SZ')
    conditions = NaivePolicyConditionField(
        many=True,
        read_only=False,
        required=False,
        queryset=EmptyQuerySet
    )

    def restore_object(self, attrs, instance=None):
        from drf_to_s3.models import Policy
        return Policy(**attrs)

    def validate(self, attrs):
        '''
        1. Disallow multiple conditions with the same element name
        2. Use introspection to validate individual conditions which are present.
        '''
        from .util import duplicates_in
        conditions = attrs.get('conditions', [])
        errors = {}
        all_names = [item.element_name for item in conditions]
        for name in duplicates_in(all_names):
            message = _('Duplicate element name')
            errors['conditions.' + name] = [message]
        for item in conditions:
            # FIXME this needs to sanitize the arguments a bit more
            # validate_condition_Content-Type -> validate_condition_Content_Type
            sanitized_element_name = item.element_name.replace('-', '_')
            condition_validate = getattr(self, "validate_condition_%s" % sanitized_element_name, None)
            if condition_validate:
                try:
                    condition_validate(item)
                except ValidationError as err:
                    field_name = 'conditions.' + item.element_name
                    errors[field_name] = errors.get(field_name, []) + list(err.messages)
        if len(errors):
            raise ValidationError(errors)
        else:
            return attrs


class APIUploadCompletionSerializer(serializers.Serializer):
    key = serializers.CharField()
    filename = serializers.CharField()

 
class FineUploadCompletionSerializer(serializers.Serializer):
    bucket = serializers.CharField()
    key = serializers.CharField()
    uuid = serializers.CharField()
    name = serializers.CharField()

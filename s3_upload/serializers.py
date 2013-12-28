from rest_framework import serializers
from django.core.exceptions import ValidationError
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

    # Subclasses should override these
    required_conditions = ['bucket']
    optional_conditions = ['Content-Type', 'success_action_status']

    # Subclasses must override this
    #   e.g. allowed_buckets = ['my-app-storage', 'my-app-secondary-storage']
    # The default will disallow all buckets.
    allowed_buckets = []

    # Subclasses must override this
    #   e.g. allowed_acls = ['public-read']
    # The default will disallow all ACLs.
    allowed_acls = []

    # Subclasses should override this
    #   e.g. allowed_success_action_redirect_values = ['/s3/success_redirect']
    # The default will disallow all values for success_action_redirect.
    allowed_success_action_redirect_values = []

    def validate_expiration(self, attrs, source):
        '''
        I suggest discarding this value entirely, and replacing
        it with a value on the server instead. Accordingly, this
        does nothing.

        Subclasses may override, though, and should either return
        attrs or raise a ValidationError.
        '''
        return attrs

    def validate_conditions(self, attrs, source):
        '''
        Instead of overriding this method, subclasses should implement
        methods like these:

            def validate_condition_bucket(self, condition):
        
        These methods should raise ValidateionError in case of errors.
        '''
        conditions = attrs[source]
        for item in conditions:
            if item.key in self.required_conditions + self.optional_conditions:
                # validate_condition_Content-Type -> validate_condition_Content_Type
                condition_validate_method_name = "validate_condition_%s" % item.key.replace('-', '_')
                condition_validate = getattr(self, condition_validate_method_name, None)
                if condition_validate:
                    try:
                        condition_validate(item)
                    except ValidationError as err:
                        self._errors[source + '.' + item.key] = list(err.messages)
            else:
                raise ValidationError(
                    _('Invalid condition key: %(key)s'),
                    params={'key': item.key},
                )
        missing_conditions = set(self.required_conditions) - set([item.key for item in conditions])
        for key in missing_conditions:
            err = ValidationError(
                _('Required condition is missing'),
            )
            self._errors[source + '.' + key] = list(err.messages)
        return attrs

    def validate_condition_acl(self, condition):
        if not isinstance(condition.value, basestring):
            raise ValidationError(
                _('ACL should be a string'),
            )
        if condition.value not in self.allowed_acls:
            raise ValidationError(
                _('ACL not allowed'),
            )

    def validate_condition_bucket(self, condition):
        if not isinstance(condition.value, basestring):
            raise ValidationError(
                _('Bucket should be a string: %(value)s'),
                params={'value': condition.value},
            )
        if condition.value not in self.allowed_buckets:
            raise ValidationError(
                _('Bucket not allowed'),
            )

    def validate_condition_Content_Type(self, condition):
        '''
        Check if this is a valid Media Type according to the RFC.
        '''
        import string
        if not isinstance(condition.value, basestring):
            raise ValidationError(
                _('Content-Type should be a string: %(value)s'),
                params={'value': condition.value},
            )
        allowed_characters = frozenset(
            string.ascii_letters +
            string.digits +
            '!' + '#' + '$' + '&' + '.' + '+' + '-' + '^' + '_'
        )
        try:
            first, rest = condition.value.split('/', 1)
        except ValueError:
            raise ValidationError(
                _('Invalid Content-Type'),
            )
        if any([char not in allowed_characters for char in first + rest]):
            raise ValidationError(
                _('Invalid Content-Type'),
            )

    def validate_condition_success_action_status(self, condition):
        if condition.value is None:
            return
        elif isinstance(condition.value, basestring):
            if not unicode(condition.value).isnumeric():
                raise ValidationError(
                    _('Invalid success_action_status'),
                )
            status_code = int(condition.value)
        elif isinstance(condition.value, int):
            status_code = condition.value
        else:
            raise ValidationError(
                _('Invalid success_action_status'),
            )
        if status_code < 200 or status_code >= 400:
            raise ValidationError(
                _('success_action_status should be between 200 and 399'),
            )

    def validate_success_action_redirect(self, condition):
        if condition.value is None:
            return
        elif not condition.value in self.allowed_success_action_redirect_values:
            raise ValidationError(
                _('Invalid allowed_success_action_redirect value'),
            )

    def validate_condition_key(self, condition):
        if not isinstance(condition.value, basestring):
            raise ValidationError(
                _('Invalid key'),
            )
        elif len(condition.value.decode('utf-8')) > 1024:
            raise ValidationError(
                _('Key too long'),
            )

    def validate_condition_x_amz_meta_qqfilename(self, condition):
        valid_characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~:/?#[]@!$&'()*+,;="
        if any([char not in valid_characters for char in condition.value]):
            raise ValidationError(
                _('Invalid character in x-amz-meta-qqfilename'),
            )

    def validate_condition_content_length_range(self, condition):
        values = condition.value is not None and [condition.value] or condition.value_range
        num_values = []
        for value in values:
            if isinstance(value, basestring):
                if not unicode(value).isnumeric():
                    raise ValidationError(
                        _('Invalid value for content_length_range'),
                    )
                num_values.append(int(value))
            elif isinstance(value, int):
                num_values.append(value)
            else:
                raise ValidationError(
                    _('Invalid value for content_length_range'),
                )
        for value in num_values:
            if value < 0:
                raise ValidationError(
                    _('content_length_range should be nonnegative'),
                )                
        if len(num_values) == 2 and num_values[0] > num_values[1]:
            raise ValidationError(
                _('content_length_range should be ordered ascending'),
            )

class FineUploaderPolicySerializer(BaseUploadPolicySerializer):
    required_conditions = [
        'acl',
        'bucket',
        'key',
        'x-amz-meta-qqfilename',
    ]
    optional_conditions = [
        'Content-Type',
        'success_action_status',
        'success_action_redirect',
        'content-length-range',
    ]


class LimitKeyToUrlCharactersMixin(object):
    def validate_condition_key(self, condition):
        super(LimitKeyToUrlCharactersMixin, self).validate_condition_key(condition)
        valid_characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~:/?#[]@!$&'()*+,;="
        if any([char not in valid_characters for char in condition.value]):
            raise ValidationError(
                _('Invalid character in key'),
            )


class MyFineUploaderPolicySerializer(LimitKeyToUrlCharactersMixin, FineUploaderPolicySerializer):
    pass


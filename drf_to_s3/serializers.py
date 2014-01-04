from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _


class UploadPolicyConditionField(serializers.RelatedField):
    '''
    Serializes an UploadPolicyCondition instance to a list
    or dictionary, and vice versa.

    It doesn't know about the schema, only about the array
    and dictionary representations. Accordingly, it raises
    ValidationError for malformed arrays and dictionaries,
    but BaseUploadPolicySerializer is responsible for
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
        from drf_to_s3.models import UploadPolicyCondition
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
        return UploadPolicyCondition(
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
        from drf_to_s3.models import UploadPolicyCondition
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
        return UploadPolicyCondition(
            operator=None,
            element_name=element_name,
            value=value,
            value_range=None
        )


class BaseUploadPolicySerializer(serializers.Serializer):
    '''
    Serializes an UploadPolicy instance to a dictionary, and
    vice versa.

    This class aims to do two things:

     1. Provide configurable validation of essentials like
        bucket and acl
     2. Provide stupid validation of variable types, that
        key and content-type are valid, and so on

    DefaultUploadPolicySerializer provides some more
    conservative defaults.

    Set a few values to control the validation:

    required_conditions: A list of required elements. Missing
      one these conditions will raise a ValidationError.
    optional_conditions: A list of optional elements. Conditions
      which are not in required_conditions or optional_conditions
      will raise a ValidationError. Default is all the keys in
      the schema. Note that condition names are case sensitive at
      the moment.
    allowed_buckets: A list of allowed S3 buckets. Subclasses must
      override, as the default is [].
    allowed_acls: A list of allowed S3 canned ACLs to set on the
      uploaded file. The default is ['private']
    allowed_success_action_redirect_values: A list of values which
      may be provided for success_action_redirect.

    e.g.

    allowed_buckets = ['my-app-storage', 'my-app-secondary-storage']
    allowed_success_action_redirect_values = ['/s3/success_redirect']

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
    conditions = UploadPolicyConditionField(
        many=True,
        read_only=False,
        required=False,
        queryset=EmptyQuerySet
    )

    required_conditions = [
        'bucket',
        'key',
    ]
    optional_conditions = [
        'content-length-range',
        'Cache-Control',
        'Content-Type',
        'Content-Disposition',
        'Content-Encoding',
        'Expires',
        'redirect',
        'success_action_redirect',
        'success_action_status',
        'x-amz-security-token',
    ]
    allowed_acls = ['private']

    @property
    def allowed_buckets(self):
        from django.conf import settings
        return settings.AWS_UPLOAD_ALLOWED_BUCKETS

    @property
    def allowed_success_action_redirect_values(self):
        from django.conf import settings
        return getattr(settings, 'AWS_UPLOAD_SUCCESS_ACTION_REDIRECT_VALUES', [])

    def restore_object(self, attrs, instance=None):
        from drf_to_s3.models import UploadPolicy
        return UploadPolicy(**attrs)

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
        1. Disallow starts-with, which complicates validation, and probably
           is unnecessary
        2. Make sure conditions are in required_conditions or optional_conditions
        3. Use introspection to validate individual conditions which are
           present
        4. Require that required_conditions are present
        '''
        conditions = attrs[source]
        for item in conditions:
            if item.has_alternate_operator():
                err = _('starts-with operator is not allowed')
                self._errors[source + '.' + item.element_name] = [err]
            elif item.element_name not in self.required_conditions + self.optional_conditions:
                err = _('Invalid element name')
                self._errors[source + '.' + item.element_name] = [err]
            else:
                # validate_condition_Content-Type -> validate_condition_Content_Type
                condition_validate_method_name = "validate_condition_%s" % item.element_name.replace('-', '_')
                condition_validate = getattr(self, condition_validate_method_name, None)
                if condition_validate:
                    try:
                        condition_validate(item)
                    except ValidationError as err:
                        self._errors[source + '.' + item.element_name] = list(err.messages)
        missing_conditions = set(self.required_conditions) - set([item.element_name for item in conditions])
        for element_name in missing_conditions:
            err = _('Required condition is missing')
            self._errors[source + '.' + element_name] = [err]
        return attrs

    def validate_condition_acl(self, condition):
        '''
        Require that acl is in the list of allowed_acls.
        '''
        if condition.value not in self.allowed_acls:
            raise ValidationError(
                _('ACL not allowed'),
            )

    def validate_condition_bucket(self, condition):
        '''
        Require that bucket is in the list of allowed_buckets.
        '''
        if condition.value not in self.allowed_buckets:
            raise ValidationError(
                _('Bucket not allowed'),
            )

    def validate_condition_Content_Type(self, condition):
        '''
        Require a valid Media Type according to the RFC.
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
        '''
        Require that success_action_status is numeric and reasonable.
        '''
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
        '''
        Require that validate_success_action_redirect is None or in
        the allowed list.
        '''
        if condition.value is None:
            return
        elif not condition.value in self.allowed_success_action_redirect_values:
            raise ValidationError(
                _('Invalid allowed_success_action_redirect value'),
            )

    def validate_condition_key(self, condition):
        '''
        Require that key is a string and not too long.

        Perhaps absurdly, S3 allows keys to be any unicode character.
        That includes unprintable characters and direction-changing
        characters, which sounds like trouble. Use
        LimitKeyToUrlCharactersMixin to provide saner validation of
        this value.
        '''
        if not isinstance(condition.value, basestring):
            raise ValidationError(
                _('Key should be a string'),
            )
        elif len(condition.value.decode('utf-8')) > 1024:
            raise ValidationError(
                _('Key too long'),
            )

    @classmethod
    def string_contains_only_url_characters(cls, string_value):
        '''
        Raise an exception if string_value contains non-URL characters.
        '''
        valid_characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~:/?#[]@!$&'()*+,;="
        return all([char in valid_characters for char in string_value])

    def validate_condition_x_amz_meta_qqfilename(self, condition):
        '''
        Require that x-amz-meta-qqfilename is a string containing
        only URL characters.
        '''
        if not isinstance(condition.value, basestring):
            raise ValidationError(
                _('x-amz-meta-qqfilename should be a string'),
            )
        if not self.string_contains_only_url_characters(condition.value):
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


class LimitKeyToUrlCharactersMixin(object):
    def validate_condition_key(self, condition):
        '''
        Require that the key is a valid URL character.

        Without this, the serializer will accept any unicode character
        in the key.
        '''
        super(LimitKeyToUrlCharactersMixin, self).validate_condition_key(condition)
        if not self.string_contains_only_url_characters(condition.value):
            raise ValidationError(
                _('Invalid character in key'),
            )


class DefaultUploadPolicySerializer(
    LimitKeyToUrlCharactersMixin,
    BaseUploadPolicySerializer
):
    '''
    Subclass this one.

     - Be sure to set the `allowed_buckets`.
     - Override `optional_conditions` to further limit them, if you like.
    '''
    pass


class FineUploaderPolicySerializer(DefaultUploadPolicySerializer):
    '''
    To be more paranoid, subclass this one. It's tailored to the
    annotated policy document given by Fine Uploader. It requires
    all the keys Fine Uploader always includes, and allows the
    keys which sometimes are included.

    http://blog.fineuploader.com/2013/08/16/fine-uploader-s3-upload-directly-to-amazon-s3-from-your-browser/#sign-policy
    '''
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


class FineUploadNotificationSerializer(serializers.Serializer):
    bucket = serializers.CharField()
    key = serializers.CharField()
    uuid = serializers.CharField()
    name = serializers.CharField()

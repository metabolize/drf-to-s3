from drf_to_s3 import naive_serializers
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _


class DefaultPolicySerializer(naive_serializers.NaivePolicySerializer):
    '''
    A reasonably secure serializer, suitable for signing upload
    requests.

    It requires that acl, bucket, and key are present, but
    expects the caller to check their values.

    It disallows some keys which are part of the schema but
    that are not essential for supporting user uploads.
    This is to avoid any surprises or security vulnerabilities
    from letting the user set these headers. If your
    application needs to set or override these values, the
    server should do so in the success callback, when it
    copies the files to permanent storage.

    - Expires

    http://blog.fineuploader.com/2013/08/16/fine-uploader-s3-upload-directly-to-amazon-s3-from-your-browser/#sign-policy

    '''
    required_conditions = [
        'acl',
        'bucket',
        'key',
    ]
    optional_conditions = [
        'Cache-Control',
        'content-length-range',
        'Content-Type',
        'Content-Disposition',
        'Content-Encoding',
        'redirect',
        'success_action_redirect',
        'success_action_status',
        'x-amz-meta-qqfilename',
        'x-amz-security-token',
    ]

    def validate(self, attrs):
        '''
        1. Disallow starts-with, which complicates validation, and
           is unnecessary for file uploading
        2. Require that required_conditions are present
        3. Make sure conditions are in required_conditions or
           optional_conditions
        4. Invoke super, which checks for duplicate keys and
           invokes the validate_condition_<element_name> methods
        '''
        conditions = attrs.get('conditions', [])
        errors = {}
        missing_conditions = set(self.required_conditions) - set([item.element_name for item in conditions])
        for element_name in missing_conditions:
            message = _('Required condition is missing')
            errors['conditions.' + element_name] = [message]
        for item in conditions:
            field_name = 'conditions.' + item.element_name
            if item.operator and item.operator != 'eq':
                message = _("starts-with and operators other than 'eq' are not allowed")
                errors[field_name] = errors.get(field_name, []) + [message]
            elif item.element_name not in self.required_conditions + self.optional_conditions:
                message = _('Invalid element name')
                errors[field_name] = errors.get(field_name, []) + [message]
        try:
            super(DefaultPolicySerializer, self).validate(attrs)
        except ValidationError as err:
            # Merge with our errors
            for field_name, error_messages in err.message_dict.items():
                errors[field_name] = errors.get(field_name, []) + list(error_messages)
        if len(errors):
            raise ValidationError(errors)
        else:
            return attrs

    def validate_condition_bucket(self, condition):
        import s3
        if (not isinstance(condition.value, basestring) or
            not s3.validate_bucket_name(condition.value)):
            raise ValidationError(
                _('Invalid bucket name'),
            )

    def validate_condition_Content_Type(self, condition):
        '''
        Require a valid Media Type according to the RFC.
        '''
        import string
        from util import string_is_valid_media_type
        if (not isinstance(condition.value, basestring) or
            not string_is_valid_media_type(condition.value)):
            raise ValidationError(
                _('Invalid Content-Type'),
            )

    def validate_condition_key(self, condition):
        '''
        Require that key is a string consisting only of URL characters
        and is not too long.

        Perhaps absurdly, S3 allows keys to be any unicode character.
        That includes unprintable characters and direction-changing
        characters, which sounds like trouble.
        '''
        from .util import string_contains_only_url_characters
        if not isinstance(condition.value, basestring):
            raise ValidationError(
                _('Key should be a string'),
            )
        elif len(condition.value.decode('utf-8')) > 1024:
            raise ValidationError(
                _('Key too long'),
            )
        if not string_contains_only_url_characters(condition.value):
            raise ValidationError(
                _('Invalid character in key'),
            )

    def validate_condition_x_amz_meta_qqfilename(self, condition):
        '''
        Require that x-amz-meta-qqfilename is a string containing
        only URL characters.
        '''
        from .util import string_is_valid_filename
        if (not isinstance(condition.value, basestring) or
            not string_is_valid_filename(condition.value)):
            raise ValidationError(
                _('Filename should not include fancy characters'),
            )

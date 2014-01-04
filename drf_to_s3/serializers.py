from rest_framework import serializers
from drf_to_s3 import naive_serializers
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _


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


class DefaultPolicySerializer(
    LimitKeyToUrlCharactersMixin,
    naive_serializers.NaivePolicySerializer
):
    '''
    Subclass this one.

     - Be sure to set the `allowed_buckets`.
     - Override `optional_conditions` to further limit them, if you like.
    '''
    pass


class FinePolicySerializer(DefaultPolicySerializer):
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

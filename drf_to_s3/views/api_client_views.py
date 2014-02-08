from django.utils.translation import ugettext as _
from rest_framework.views import APIView
from drf_to_s3.views import BaseUploadCompletionView


class SignedPutURIView(APIView):
    '''
    Generate a signed url for the user to upload a file to S3.

    '''
    expire_after_seconds = 300

    def get_aws_upload_bucket(self):
        from django.conf import settings
        return settings.AWS_UPLOAD_BUCKET

    def get_aws_access_key_id(self):
        from django.conf import settings
        return settings.AWS_UPLOAD_ACCESS_KEY_ID

    def get_aws_secret_key(self):
        from django.conf import settings
        return settings.AWS_UPLOAD_SECRET_ACCESS_KEY

    def post(self, request):
        import uuid
        from rest_framework import status
        from rest_framework.response import Response
        from drf_to_s3 import s3
        from drf_to_s3.access_control import upload_prefix_for_request

        key = '%s/%s' % (upload_prefix_for_request(request), str(uuid.uuid4()))
        upload_uri = s3.build_signed_upload_uri(
            bucket=self.get_aws_upload_bucket(),
            key=key,
            access_key_id=self.get_aws_access_key_id(),
            secret_key=self.get_aws_secret_key(),
            expire_after_seconds=self.expire_after_seconds
        )
        data = {
            'key': key,
            'upload_uri': upload_uri,
        }
        return Response(data=data, status=status.HTTP_200_OK)


class APIErrorResponseMixin(object):
    '''
    For compatibility with FineUploaderErrorResponseMixin.

    '''
    def handle_validation_error(self, serializer):
        from rest_framework import status
        from rest_framework.response import Response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class APIUploadCompletionView(APIErrorResponseMixin, BaseUploadCompletionView):
    '''
    Handle the upload success callback from the API client. 
    Expected simpler serializer, client should extend this view and provide check_upload_permissions 
    '''
    from drf_to_s3.naive_serializers import APIUploadCompletionSerializer
    serializer_class = APIUploadCompletionSerializer

    def get_aws_upload_bucket(self):
        from django.conf import settings
        return settings.AWS_UPLOAD_BUCKET

    def post(self, request, format=None):
        from rest_framework import status
        from rest_framework.response import Response
        from rest_framework.exceptions import PermissionDenied

        serializer = self.serializer_class(data=request.DATA)
        if not serializer.is_valid():
            return self.handle_validation_error(serializer)
        # Allow extending the serializer to return a list of
        # objects. Return attrs as the first object and this
        # will continue to work.
        if isinstance(serializer.object, list):
            attrs = serializer.object[0]
        else:
            attrs = serializer.object

        bucket = self.get_aws_upload_bucket()
        key = attrs['key']
        filename = attrs['filename']

        self.check_upload_permissions(request, bucket, key)
        
        return self.handle_upload(request, serializer, serializer.object, 
                                  bucket, key, filename)

from django.utils.translation import ugettext as _
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import StaticHTMLRenderer
from rest_framework.views import APIView

class FineUploaderErrorResponseMixin(object):

    def make_error_response(self, request, serializer=None, exception=None, compatibility_for_iframe=False):
        '''
        This implementation is designed for Fine Uploader,
        which expects `invalid: True`.
        FIXME this should provide a user-readable 'error' message.
        '''
        from rest_framework import status
        from rest_framework.response import Response
        response = {
            'invalid': True,
        }
        if exception is not None:
            response['error'] = exception.detail
        if serializer is not None:
            response['errors'] = serializer.errors
        status = status.HTTP_200_OK if compatibility_for_iframe else status.HTTP_400_BAD_REQUEST
        return Response(response, status=status)


class FineSignPolicyView(FineUploaderErrorResponseMixin, APIView):
    '''
    aws_secret_access_key: Your AWS secret access key, preferably
      for an account which only has put privileges. Subclasses
      may override and set this property, or else it will pull
      from settings.AWS_UPLOAD_SECRET_ACCESS_KEY.
    expire_after_seconds: Number of seconds before signed policy
      documents should expires. Used by pre_sign.
    '''
    from rest_framework.parsers import JSONParser
    from rest_framework.renderers import JSONRenderer
    from drf_to_s3.serializers import DefaultPolicySerializer

    expire_after_seconds = 300
    serializer_class = DefaultPolicySerializer
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer,)

    def get_aws_secret_access_key(self):
        from django.conf import settings
        return settings.AWS_UPLOAD_SECRET_ACCESS_KEY

    def check_policy_permissions(self, request, upload_policy):
        '''
        Given a valid upload policy, check that the user
        has permission to upload to the given bucket,
        path, etc.
        '''
        from drf_to_s3.access_control import check_policy_permissions
        check_policy_permissions(request, upload_policy)

    def pre_sign(self, upload_policy):
        '''
        Amend the policy before signing. This overrides the
        policy expiration time.
        '''
        from drf_to_s3 import s3
        upload_policy.expiration = s3.utc_plus(self.expire_after_seconds)

    def post(self, request, format=None):
        from rest_framework import status
        from rest_framework.response import Response
        from drf_to_s3 import s3

        request_serializer = self.serializer_class(data=request.DATA)
        if not request_serializer.is_valid():
            return self.make_error_response(request, serializer=request_serializer)
        upload_policy = request_serializer.object

        self.check_policy_permissions(request, upload_policy)
        self.pre_sign(upload_policy)

        policy_document = self.serializer_class(upload_policy).data
        signed_policy = s3.sign_policy_document(
            policy_document=policy_document,
            secret_key=self.get_aws_secret_access_key()
        )
        response = {
            'policy': signed_policy['policy'],
            'signature': signed_policy['signature'],
            'policy_decoded': policy_document,
            # Provide this to assist with debugging and testing
        }
        return Response(response)


@api_view(('GET',))
@renderer_classes((StaticHTMLRenderer,))
def empty_html(request):
    from rest_framework.response import Response
    return Response('')

# def empty_html(request):
#     from django.http import HttpResponse
#     return HttpResponse('', content_type='text/html')


class FineUploadCompletionView(FineUploaderErrorResponseMixin, APIView):
    '''
    Handle the upload complete notification from the
    client.

    Designed for use with a separate upload folder or
    separate bucket, so it also copies the file to the
    staging bucket.

    You can subclass this and override handle_upload to
    copy the file to the staging bucket (since the
    upload goes to a temporary path), create any
    necessary objects on the server, or return
    additional information to the client.

    '''
    from rest_framework.parsers import FormParser
    from rest_framework.renderers import JSONRenderer
    from drf_to_s3.naive_serializers import FineUploadCompletionSerializer

    parser_classes = (FormParser,)
    renderer_classes = (JSONRenderer,)
    serializer_class = FineUploadCompletionSerializer

    def get_aws_storage_bucket(self):
        from django.conf import settings
        return settings.AWS_STORAGE_BUCKET_NAME

    def check_upload_permissions(self, request, obj):
        '''
        Check a deserialized request, check that the user has
        permission to upload to the given bucket and key.

        '''
        from drf_to_s3.access_control import check_upload_permissions
        check_upload_permissions(request, obj['bucket'], obj['key'])

    def copy_upload_to_storage(self, request, bucket, key, uuid, name, etag):
        '''
        '''
        import uuid as _uuid
        from drf_to_s3 import s3
        target
        s3.copy(
            src_bucket=bucket,
            src_key=key,
            etag=etag,
            dst_bucket=self.bucket,
            dst_key=self.nonexisting_key
        )

    def handle_upload(self, request, bucket, key, uuid, name):
        '''
        Subclasses should override, to provide handling for the
        successful upload.

        Subclasses may invoke invoke copy_upload_to_storage()
        to use the default logic, or use their own.

        Return a response with status=status.HTTP_200_OK.

        Return a specific error message in the `error` key.
        Under IE9 and IE8, if you return a non-200 status,
        only a generic error message can be displayed. To
        show a detailed error message, return a response
        with 200 status and an `error` key set.
        http://blog.fineuploader.com/2013/08/16/fine-uploader-s3-upload-directly-to-amazon-s3-from-your-browser/#success-endpoint

        make_error_response will do this with
        compatibility_for_iframe=True.

        Any other content you provide in the response is passed
        to the `complete` handler on the client.
        http://docs.fineuploader.com/api/events.html#complete

        request: The Django request
        bucket: S3 bucket
        key: Key name of the associated file in S3
        uuid: UUID of the file
        name: Name of the file
        etag: The S3 etag of the S3 key

        Depending what you do with the uploaded file, you may
        need to validate that the request originated by this
        user, to prevent a malicious user from using this
        callback to hijack someone else's upload.

        Note: To avoid the need to configure the client to
        produce the prefixed upload URL, I'd rather
        prevent highjacking (due to vulnerable uuid
        generation) by having the client send the
        etag (which S3 provides to the client after a
        successful upload) in the completion handler.

        '''
        import os, uuid
        from rest_framework import status
        from rest_framework.response import Response
        from drf_to_s3 import s3

        basename, ext = os.path.splitext(name)
        new_key = str(uuid.uuid4()) + ext
        try:
            s3.copy(
                src_bucket=bucket,
                src_key=key,
                dst_bucket=self.get_aws_storage_bucket(),
                dst_key=new_key
            )
        except s3.ObjectNotFoundException as e:
            return self.make_error_response(
                request=request,
                exception=e,
                compatibility_for_iframe=True
            )

        return Response(status=status.HTTP_200_OK)

    def post(self, request, format=None):
        from rest_framework import status
        from rest_framework.response import Response
        from rest_framework.exceptions import PermissionDenied

        serializer = self.serializer_class(data=request.DATA)
        if not serializer.is_valid():
            return self.make_error_response(
                request=request,
                exception=e,
                compatibility_for_iframe=True
            )
        obj = serializer.object

        try:
            self.check_upload_permissions(request, obj)
        except PermissionDenied as e:
            return self.make_error_response(
                request=request,
                exception=e,
                compatibility_for_iframe=True
            )

        return self.handle_upload(request, **obj)

from django.utils.translation import ugettext as _
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import StaticHTMLRenderer
from rest_framework.views import APIView


class FineUploaderSignUploadPolicyView(APIView):
    '''
    serializer_class: Your subclass of DefaultUploadPolicySerializer
      or FineUploaderPolicySerializer. Default is None; subclasses
      must override, and at a minimum set allowed_buckets.
    aws_secret_access_key: Your AWS secret access key, preferably
      for an account which only has put privileges. Subclasses
      may override and set this property, or else it will pull
      from settings.AWS_UPLOAD_SECRET_ACCESS_KEY.
    expire_after_seconds: Number of seconds before signed policy
      documents should expires. Used by pre_sign.
    '''
    from rest_framework.parsers import JSONParser
    from rest_framework.renderers import JSONRenderer
    from drf_to_s3.serializers import FineUploaderPolicySerializer

    expire_after_seconds = 300
    serializer_class = FineUploaderPolicySerializer
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer,)

    @property
    def aws_secret_access_key(self):
        from django.conf import settings
        return settings.AWS_UPLOAD_SECRET_ACCESS_KEY

    def pre_sign(self, upload_policy):
        import datetime
        expiration = datetime.datetime.today() + datetime.timedelta(0, self.expire_after_seconds)
        upload_policy.expiration = expiration

    def post(self, request, format=None):
        from rest_framework import status
        from rest_framework.response import Response
        from drf_to_s3.utils import sign_policy_document

        request_serializer = self.serializer_class(data=request.DATA)
        if not request_serializer.is_valid():
            response = {
                'invalid': True,
                'errors': request_serializer.errors,
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        upload_policy = request_serializer.object
        self.pre_sign(upload_policy)
        response_serializer = self.serializer_class(upload_policy)
        response = sign_policy_document(
            policy_document=response_serializer.data,
            secret_key=self.aws_secret_access_key
        )
        # We add this to assist with debugging and testing
        response['policy_decoded'] = response_serializer.data

        return Response(response)


@api_view(('GET',))
@renderer_classes((StaticHTMLRenderer,))
def empty_html(request):
    from rest_framework.response import Response
    return Response('')

# def empty_html(request):
#     from django.http import HttpResponse
#     return HttpResponse('', content_type='text/html')


class FineUploaderUploadNotificationView(APIView):
    '''
    Handle the upload complete notification from the
    client. You can subclass this and override
    handle_upload to handle the notification or to
    return additional information to the client.

    '''
    from rest_framework.parsers import FormParser
    from rest_framework.renderers import JSONRenderer

    parser_classes = (FormParser,)
    renderer_classes = (JSONRenderer,)

    def handle_upload(self, request, bucket, key, uuid, name):
        '''
        Subclasses should override, to provide handling for the
        successful upload.

        Return a response with status=status.HTTP_200_OK.

        Return a specific error message in the `error` key.
        Under IE9 and IE8, you must return a 200 status with
        `error` set, or else Fine Uploader can only display
        a generic error message.

        Any other content you provide in the response is passed
        to the `complete` handler on the client.
        http://docs.fineuploader.com/api/events.html#complete

        request: The Django request
        bucket: S3 bucket
        key: Key name of the associated file in S3
        uuid: UUID of the file
        name: Name of the file

        Depending what you do with the uploaded file, you may
        need to validate that the request originated by this
        user, to prevent a malicious user from using this
        callback to hijack someone else's upload.

        '''
        from rest_framework import status
        from rest_framework.response import Response
        return Response(status=status.HTTP_200_OK)

    def post(self, request, format=None):
        from rest_framework import status
        from rest_framework.response import Response
        from drf_to_s3.serializers import FineUploadNotificationSerializer
        serializer = FineUploadNotificationSerializer(data=request.DATA)
        if not serializer.is_valid():
            response = {
                'error': 'Malformed upload notification request',
                'errors': serializer.errors,
            }
            # Return 200 for better presentation of errors under IE9 and IE8
            # http://blog.fineuploader.com/2013/08/16/fine-uploader-s3-upload-directly-to-amazon-s3-from-your-browser/#success-endpoint
            return Response(response, status=status.HTTP_200_OK)
        return self.handle_upload(request, **serializer.object)

from django.utils.translation import ugettext as _
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import StaticHTMLRenderer
from rest_framework.views import APIView
from drf_to_s3.views import BaseUploadCompletionView


class FineUploaderErrorResponseMixin(object):
    def handle_validation_error(self, serializer):
        from rest_framework import status
        from rest_framework.response import Response
        response = {
            'invalid': True,
        }

        response['errors'] = serializer.errors
        response['error'] = ("Unable to complete your request. Errors with %s" %
                                 ', '.join(serializer.errors.keys()))
        if self.compatibility_for_iframe:   
            status_code = status.HTTP_200_OK
        else: 
            status_code = status.HTTP_400_BAD_REQUEST
        return Response(response, status=status_code)

    def handle_exception(self, exc):
        '''
        This implementation is designed for Fine Uploader,
        which expects `invalid: True`.
        FIXME this should provide a user-readable 'error' message.
        '''
        from rest_framework import status
        from rest_framework.exceptions import APIException
        from rest_framework.response import Response
        response = {
            'invalid': True,
        }

        if isinstance(exc, APIException):
            response['error'] = exc.detail
        else:
            response['error'] = 'Unable to complete your request.'

        if self.compatibility_for_iframe:
            status_code = status.HTTP_200_OK
        elif isinstance(exc, APIException):
            status_code = exc.status_code
        else:
            status_code = status.HTTP_400_BAD_REQUEST

        return Response(response, status=status_code)


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

    compatibility_for_iframe = False

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
        from rest_framework.exceptions import PermissionDenied
        from rest_framework.response import Response
        from drf_to_s3 import s3

        request_serializer = self.serializer_class(data=request.DATA)
        if not request_serializer.is_valid():
            return self.handle_validation_error(request_serializer)
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


class FineUploadCompletionView(FineUploaderErrorResponseMixin, BaseUploadCompletionView):
    '''
    Handle the upload complete notification from the
    browser client.

    Designed for use with a separate upload folder or
    separate bucket, so it also copies the file to the
    staging bucket.

    You can subclass this and override handle_upload to
    copy the file to the staging bucket (since the
    upload goes to a temporary path), create any
    necessary objects on the server, or return
    additional information to the client.

    If you subclass this and are passing dictionaries as
    attributes, you may want to use parsers.NestedFormParser,
    which will automatically unpack attributes into
    dictionaries, and allow your serializers to 

    '''
    from rest_framework.parsers import FormParser
    from rest_framework.renderers import JSONRenderer
    from drf_to_s3.naive_serializers import FineUploadCompletionSerializer

    parser_classes = (FormParser,)
    renderer_classes = (JSONRenderer,)
    serializer_class = FineUploadCompletionSerializer

    compatibility_for_iframe = True
    
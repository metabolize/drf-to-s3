from django.utils.translation import ugettext as _
from rest_framework.decorators import api_view
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
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
    serializer_class = None # Subclasses must override
    expire_after_seconds = 300
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer,)

    @property
    def aws_secret_access_key(self):
        from django.conf import settings
        return settings.AWS_UPLOAD_SECRET_ACCESS_KEY

    def get_serializer_class(self):
        from django.core.exceptions import ImproperlyConfigured
        if self.serializer_class is None:
            raise ImproperlyConfigured(
                    _('Subclasses must override serializer_class')
                )
        return self.serializer_class

    def pre_sign(self, upload_policy):
        import datetime
        expiration = datetime.datetime.today() + datetime.timedelta(0, self.expire_after_seconds)
        upload_policy.expiration = expiration

    def post(self, request, format=None):
        from rest_framework import status
        from rest_framework.response import Response
        from s3_upload.utils import sign_policy_document

        request_serializer = self.get_serializer_class()(data=request.DATA)
        if not request_serializer.is_valid():
            response = {
                'invalid': True,
                'errors': request_serializer.errors,
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        upload_policy = request_serializer.object
        self.pre_sign(upload_policy)
        response_serializer = self.get_serializer_class()(upload_policy)
        response = sign_policy_document(
            policy_document=response_serializer.data,
            secret_key=self.aws_secret_access_key
        )
        # We add this to assist with debugging and testing
        response['policy_decoded'] = response_serializer.data

        return Response(response)


def empty_html(request):
    from django.http import HttpResponse
    return HttpResponse('', content_type='text/html')

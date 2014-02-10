from django.utils.translation import ugettext as _
from rest_framework.views import APIView


class BaseUploadCompletionView(APIView):
    '''
    Abstract base class for the upload process. Provide some common attributes 
    and methods for Upload completion view for both brower and public api consumer.
    Compatibility_for_iframe is used for FineUploaderErrorResponseMixin. Subclass can
    override it for browsers compatibility
    '''
    compatibility_for_iframe = False

    def get_aws_storage_bucket(self):
        from django.conf import settings
        return settings.AWS_STORAGE_BUCKET_NAME

    def check_upload_permissions(self, request, bucket, key):
        from drf_to_s3.access_control import check_upload_permissions
        check_upload_permissions(request, bucket, key)

    # def copy_upload_to_storage(self, request, bucket, key, uuid, name, etag):
    #     '''
    #     '''
    #     import uuid as _uuid
    #     from drf_to_s3 import s3
    #     s3.copy(
    #         src_bucket=bucket,
    #         src_key=key,
    #         etag=etag,
    #         dst_bucket=self.bucket,
    #         dst_key=self.nonexisting_key
    #     )

    def handle_upload(self, request, serializer, obj, bucket, key, filename):
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
        from django.conf import settings

        basename, ext = os.path.splitext(filename)
        new_key = str(uuid.uuid4()) + ext
        
        s3.copy(
            src_bucket=bucket,
            src_key=key,
            dst_bucket=self.get_aws_storage_bucket(),
            dst_key=new_key
        )
     
        return Response(status=status.HTTP_200_OK)

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
        
        bucket = attrs['bucket']
        key = attrs['key']
        filename = attrs['name']
        
        self.check_upload_permissions(request, bucket, key)

        return self.handle_upload(request, serializer, serializer.object,
                                  bucket, key, filename)

class UploadPrefixMiddleware(object):
    '''
    Sets a cookie with the upload prefix.

    To be agnostic about your method of user authentication, this is
    handled using middleware. It can't be in a signal, since the signal
    handler doesn't have access to the response.

    In most applications, the client already has access to a
    normalized username, so you probably don't need this at
    all.

    To use this, add it to your MIDDLEWARE_CLASSES:

        MIDDLEWARE_CLASSES = (
            ...
            'drf_to_s3.middleware.UploadPrefixMiddleware',
            ...
        )

    '''

    def process_response(self, request, response):
        from django.conf import settings
        from rest_framework.exceptions import PermissionDenied
        from .access_control import upload_prefix_for_request

        cookie_name = getattr(settings, 'UPLOAD_PREFIX_COOKIE_NAME', 'upload_prefix')
        try:
            response.set_cookie(cookie_name, upload_prefix_for_request(request))
        except PermissionDenied:
            response.delete_cookie(cookie_name)
        return response

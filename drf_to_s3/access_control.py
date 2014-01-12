from django.utils.translation import ugettext as _


def upload_bucket():
    '''
    The upload bucket. Exposed here for convenience, as you
    may need to send it to the client to easily dev/prod
    configuration.
    '''
    from django.conf import settings
    return settings.AWS_UPLOAD_BUCKET

def upload_prefix_for_request(request):
    '''
    Return a string which the user should prepend to all S3
    keys for upload. By creating a separate namespace for
    each user, you prevent a malicious user from hijacking or
    claiming another user's uploads.

    FIXME needs its own test?

    '''
    from django.conf import settings
    from rest_framework.exceptions import PermissionDenied

    # Allow the user to specify their own function
    prefix_func = getattr(settings, 'AWS_UPLOAD_PREFIX_FUNC', None)
    if prefix_func is not None:
        return prefix_func(request)

    if not request.user.is_authenticated():
        raise PermissionDenied(_('Log in before uploading'))

    return request.user.get_username()

def check_policy_permissions(request, upload_policy):
    '''
    Check permissions on the given upload policy. Raises
    rest_framework.exceptions.PermissionDenied in case
    of error.

    The acl must be 'private'. Uploading public files
    using this API is a bad idea. By its nature, the
    API will allow any user to upload any file. If
    files are public that likely means you're exposing
    the keys publicly, which means the files are
    easily replaced by a user of this very API.

    '''
    from rest_framework.exceptions import PermissionDenied
    if upload_policy['acl'].value != 'private':
        raise PermissionDenied(_("ACL should be 'private'"))
    check_upload_permissions(
        request=request,
        bucket=upload_policy['bucket'].value,
        key=upload_policy['key'].value
    )

def check_upload_permissions(request, bucket, key):
    '''
    Check permissions on the given upload policy. Raises
    rest_framework.exceptions.PermissionDenied in case
    of error.

    '''
    from django.core.exceptions import ImproperlyConfigured
    from rest_framework.exceptions import PermissionDenied
    if bucket != upload_bucket():
        raise PermissionDenied(_("Bucket should be '%s'" % upload_bucket()))
    upload_prefix = upload_prefix_for_request(request)
    if upload_prefix is None or len(upload_prefix) == 0:
        raise ImproperlyConfigured(
            _('Upload prefix must be non-zero-length and should be unique for each user')
        )
    if not key.startswith(upload_prefix):
        raise PermissionDenied(_("Key should start with '%s/'" % upload_prefix))

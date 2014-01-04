from django.utils.translation import ugettext as _


def upload_bucket():
    from django.conf import settings
    return settings.AWS_UPLOAD_BUCKET

def upload_prefix_for_user(user):
    '''
    Return a string which the user should prepend to all S3
    keys for upload. By creating a separate namespace for
    each user, you prevent a malicious user from hijacking or
    claiming another user's uploads.

    '''
    from django.conf import settings
    if hasattr(settings, 'S3_UPLOAD_PREFIX_FUNC'):
        return settings.S3_UPLOAD_PREFIX_FUNC(user)
    else:
        return settings.S3_UPLOAD_KEY_PREFIX + user.username

def check_permissions(user, upload_policy):
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
    if upload_policy['bucket'].value != upload_bucket():
        raise PermissionDenied(_("Bucket should be '%s'" % upload_bucket()))

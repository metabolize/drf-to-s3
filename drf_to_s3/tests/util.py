def establish_session(original_function):
    '''
    Simulate establishing a session.

    Adapted from https://code.djangoproject.com/ticket/10899 and
    http://blog.joshcrompton.com/2012/09/how-to-use-sessions-in-django-unit-tests.html

    FIXME this needs its own tests

    '''
    def new_function(self, *args, **kwargs):
        from importlib import import_module
        from django.conf import settings

        engine = import_module(settings.SESSION_ENGINE)
        store = engine.SessionStore()
        store.save()  # we need to make load() work, or the cookie is worthless

        self.client.cookies[settings.SESSION_COOKIE_NAME] = store.session_key
        self.session_key = store.session_key

        original_function(self, *args, **kwargs)
    return new_function

def get_user_model():
    try:
        from django.contrib.auth import get_user_model
    except ImportError: # django < 1.5
        from django.contrib.auth.models import User
        return User
    else:
        return get_user_model()

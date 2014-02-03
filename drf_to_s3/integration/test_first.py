import os, time, unittest
from django.conf import settings
from django.conf.urls import include, patterns, url
from django.test import LiveServerTestCase
from django.test.utils import override_settings
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait # available since 2.4.0
from selenium.webdriver.support import expected_conditions as EC # available since 2.26.0
from drf_to_s3.views import FineUploadCompletionView


def create_random_temporary_file():
    '''
    Create a temporary file with random contents, and return its path.

    The caller is responsible for removing the file when done.
    '''
    def random_line():
        import random, string
        return ''.join(random.choice(string.ascii_letters) for x in range(80))
    import tempfile
    with tempfile.NamedTemporaryFile('w', delete=False) as f:
        f.write('\n'.join(random_line() for x in range(30)))
        return f.name


class LoginPage(object):
    '''
    Page object for the login page.

    '''
    def __init__(self, driver):
        self.username = driver.find_element_by_id('id_username')
        self.password = driver.find_element_by_id('id_password')


class UploadPage(object):
    '''
    Page object for the upload page.

    '''
    def __init__(self, driver):
        self.uploader = driver.find_element_by_id('fine-uploader')
        self.input_file = driver.find_element_by_xpath("//input[@type='file']")
        self.driver = driver

    def get_file_list_item(self, file_id):
        return self.driver.find_element_by_xpath("//li[@qq-file-id='%s']" % file_id)


def server_settings_js(request):
    import json
    from django.conf import settings
    from django.http import HttpResponse
    server_settings = {
        'upload_bucket': settings.AWS_UPLOAD_BUCKET,
        's3_access_key': settings.AWS_UPLOAD_ACCESS_KEY_ID,
    }
    script = 'var server_settings = %s ;' % json.dumps(server_settings)
    return HttpResponse(script, content_type='text/javascript')

urlpatterns = patterns('',
    url(r'^server_settings', server_settings_js),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api/s3/', include('drf_to_s3.urls')),
    url(r'^api/s3/file_uploaded', FineUploadCompletionView.as_view()),
)

@override_settings(
    LOGIN_REDIRECT_URL='/static/fine-jquery.html',
    MIDDLEWARE_CLASSES=settings.MIDDLEWARE_CLASSES + ('drf_to_s3.middleware.UploadPrefixMiddleware',),
    AWS_UPLOAD_BUCKET=os.environ.get('AWS_TEST_BUCKET', 'drf-to-s3-test'),
    AWS_STORAGE_BUCKET_NAME=os.environ.get('AWS_TEST_BUCKET', 'drf-to-s3-test'),
    AWS_UPLOAD_ACCESS_KEY_ID=os.environ['AWS_ACCESS_KEY_ID'],
    AWS_UPLOAD_SECRET_ACCESS_KEY=os.environ['AWS_SECRET_ACCESS_KEY']
)
class FineTest(LiveServerTestCase):
    driver = None
    urls = __name__

    def setUp(self):
        from drf_to_s3.tests.util import get_user_model
        self.username = 'frodo'
        self.password = 'shire1234'
        user = get_user_model().objects.create_user(
            username=self.username,
            password=self.password
        )
        self.test_file = create_random_temporary_file()

    def tearDown(self):
        if self.driver is not None:
            self.driver.quit()
        os.remove(self.test_file)

    @classmethod
    def create_remote_driver(cls, capabilities):
        import urlparse
        username = os.environ['SAUCE_USERNAME']
        access_key = os.environ['SAUCE_ACCESS_KEY']
        if os.environ.get('CI', False):
            capabilities['build'] = os.environ['TRAVIS_BUILD_NUMBER']
            capabilities['tags'] = [os.environ['TRAVIS_PYTHON_VERSION'], 'CI']
            capabilities['tunnel-identifier'] = os.environ['TRAVIS_JOB_NUMBER']    
            hub_url = "%s:%s@localhost:4445" % (username, access_key)
        else:
            hub_url = "%s:%s@ondemand.saucelabs.com:80" % (username, access_key)
        return webdriver.Remote(
            desired_capabilities=capabilities,
            command_executor=str("http://%s/wd/hub" % hub_url)
        )

    @classmethod
    def create_driver(cls):
        remote = os.environ.get('CI', False) or os.environ.get('WITH_SAUCE', False)
        if remote:
            print 'Using Sauce Labs'
            capabilities = webdriver.DesiredCapabilities.CHROME
            capabilities['platform'] = 'Windows 8'
            capabilities['version'] = '31'
            driver = cls.create_remote_driver(capabilities)
            driver.implicitly_wait(30)
            return driver
        else:
            return webdriver.Chrome()
    
    def test_upload(self):
        self.driver = self.create_driver()

        self.driver.get(self.live_server_url + '/api-auth/login/')
        login_page = LoginPage(self.driver)
        login_page.username.send_keys(self.username)
        login_page.password.send_keys(self.password)
        login_page.password.submit()

        # Redirects to the upload page
        WebDriverWait(self.driver, 10).until(EC.title_contains('Integration Test'))

        upload_page = UploadPage(self.driver)
        upload_page.input_file.send_keys(self.test_file)

        # Upload starts automatically
        time.sleep(2)

        list_item = upload_page.get_file_list_item(0)
        self.assertIn('qq-upload-success', list_item.get_attribute('class'))
        print 'Looks good.'
        time.sleep(2) # Show off the results

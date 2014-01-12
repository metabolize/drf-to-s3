import os, unittest
from django.conf.urls.static import static
from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait # available since 2.4.0
from selenium.webdriver.support import expected_conditions as EC # available since 2.26.0

# class SeleniumTest(unittest.TestCase):

#     @skip('')
#     def test_selenium(self):

#         # Create a new instance of the Firefox driver
#         driver = webdriver.Firefox()

#         # go to the google home page
#         driver.get("http://www.google.com")

#         # find the element that's name attribute is q (the google search box)
#         inputElement = driver.find_element_by_name("q")

#         # type in the search
#         inputElement.send_keys("cheese!")

#         # submit the form (although google automatically searches now without submitting)
#         inputElement.submit()

#         # the page is ajaxy so the title is originally this:
#         print driver.title

#         try:
#             # we have to wait for the page to refresh, the last thing that seems to be updated is the title
#             WebDriverWait(driver, 10).until(EC.title_contains("cheese!"))

#             self.assertEquals(driver.title, 'cheese! - Google Search')

#         finally:
#             driver.quit()

class FineTest(LiveServerTestCase):
    driver = None

    def setUp(self):
        self.url = self.live_server_url + '/static/fine-jquery.html'

    def tearDown(self):
        if self.driver is not None:
            self.driver.quit()
    
    def test_upload(self):
        self.driver = webdriver.Firefox()
        self.driver.get(self.url)
        uploader = self.driver.find_element_by_id('fine-uploader')

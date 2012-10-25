from two.ol.base import BaseDispatcher, RESTLikeHandler, FormHandler
from two.ol.base import FormDispatcher, RESTLikeDispatcher

from django.test.client import RequestFactory

class TestRESTHandler(RESTLikeHandler):
    pass

class TestFormHandler(FormHandler):
    pass

class TestFormDispatcher(FormDispatcher):
    pass

class TestRESTLikeDispatcher(RESTLikeDispatcher):
    pass

class TestDispatcher(object):
    def setup(self):
        self.factory = RequestFactory()

    def test_one(self, client):
        request = self.factory.get('/foo')
        instance = object()
        post = False
        rest = ""
        path = ""

        h = TestRESTHandler # (request, instance, post, rest, path)
        d = TestRESTLikeDispatcher(h, 'foo')

        d(request, "/foo/bar", a="bla")

    ## test request on /, path=""

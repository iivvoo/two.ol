from django.template import RequestContext, loader
from django.http import HttpResponse
from django.core.context_processors import csrf
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect
from django.http import HttpResponseNotFound, HttpResponseForbidden
from django.contrib.sites.models import get_current_site

import os
import types
import urllib
import json as jsonlib

## "Twool" / 2ol it takes two to django 
## Toolkit for Web Oriented Object Library
## 

def json(f):
    def jsonify(*args, **kw):
        return HttpResponse(jsonlib.dumps(f(*args, **kw)))
    return jsonify

## applypost, applyget, applyform?
def applyrequest(f):
    ## XXX positional arguments don't work, see reset.py -> process
    def applicator(self, *args, **kw):
        ##
        ## Improvements: figure out which arguments don't
        ## have defaults, provide proper error if missing
        request = self.request
        vars = f.func_code.co_varnames[:f.func_code.co_argcount]
        args = args[:]
        kw = kw.copy()
        _marker = object()
        for k in vars:
            v = request.REQUEST.get(k, _marker)
            if v is not _marker:
                kw[k] = v
        return f(self, *args, **kw)

    return applicator
##
## @expose decorator that allows you to pass an entire class to 
## context, only exposing decorated methods

def context(f):
    f.contextified = True
    return f

## Mapping is partially mimicing django's url naming/reverse. Use that
## in stead.
def Mapping(path, handlerklass):
    ## path/url stuff is still a bit messy.
    path = path.strip("/")
    if path:
        pattern = "^%s/(.*)$" % path
    else:
        pattern = "^(.*)$"
        # pattern = "^$"
    handler = handlerklass.dispatcher(handlerklass, path=path)
    return (pattern, handler)

class BaseException(Exception):
    pass

class Redirect(BaseException):
    def __init__(self, url, permanent=False):
        self.url = url
        self.permanent = permanent

class NotFound(BaseException):
    pass

class Forbidden(BaseException):
    pass

class BaseHandler(object):
    formclass = None
    model = None
    path = '/'
    template_ns = None

    def __init__(self, request, instance=None, post=False, rest=[], path=None):
        self.request = request
        self.context = RequestContext(request)

        self.update_context(request)

        self.instance = instance
        self.post = post
        self.rest = rest
        self.path = path or self.path

        self.verify_access(instance)

        self.messages = {}
        self.context['piggyback'] = {}

        if self.formclass:
            if post:
                if instance:
                    self.form = self.formclass(data=request.POST, instance=instance)
                else:
                    self.form = self.formclass(data=request.POST)
            else:
                if instance:
                    self.form = self.formclass(instance=instance)
                else:
                    self.form = self.formclass()
        else:
            self.form = None
        self.context['form'] = self.form
        self.context['instance'] = instance
        for a in dir(self):
            m = getattr(self, a)
            if isinstance(m, (types.FunctionType, types.MethodType)) and \
               getattr(m, 'contextified', False):
                self.context[a] = m

    def update_context(self, request):
        """ hook to add more stuff into context """
        pass

    def verify_access(self, instance):
        """ verify if user has access to object in current context """
        ## return self.forbidden() if not
        return True

    def set_message(self, type, message):
        self.messages[type] = message

    def get_message(self, type):
        return self.messages.get(type, '') or self.request.REQUEST.get(type, '')

    @context
    def user(self):
        return self.request.user

    @context
    def info_message(self):
        return self.get_message('info')

    @context
    def success_message(self):
        return self.get_message('success')

    @context
    def warning_message(self):
        return self.get_message('warning')

    @context
    def error_message(self):
        return self.get_message('error')

    @property
    def site(self):
        return get_current_site(self.request)

    @context
    def url(self, *elements):
        # XXX is_secure / https
        p = "http://%s/" % self.site.domain

        if self.path.strip('/'):
            p += self.path + '/' # must end in slash

        if elements:
            p += "/".join(elements) # shouldn't (?) need to end in slash
        return p

    @property
    def var(self):
        """ allows you to do 
                self.var.some_key
            in stead of
                self.request.REQUEST.get(some_key)
            raises AttributeError if some_key does not exist
        """
        class wrapper(object):
            def __init__(self, request):
                self.request = request

            def __getattr__(self, key):
                _marker = object()
                value = self.request.REQUEST.get(key, _marker)
                if value is _marker:
                    raise AttributeError(key)
                return value
        return wrapper(self.request)

    def vars(self, key, default=None):
        return self.request.REQUEST.get(key, default)

    def piggyback(self, *arguments):
        """ The piggyback can be used to store arguments that need to survive
            redirects and formposts """
        piggyback = self.context['piggyback']
        for argument in arguments:
            if argument in self.request.REQUEST:
                piggyback[argument] = self.request.REQUEST[argument]

    @classmethod
    def coerce(cls, i):
        try:
            return cls.model.objects.get(id=int(i))
        except ValueError:
            return None
        except cls.model.DoesNotExist:
            ## can't call self.notfound since we're a classmethod
            raise NotFound()

    def redirect(self, url, permanent=False, hash=None, piggyback=False, **kw):
        args = kw.copy()
        if piggyback:
            args.update(self.context['piggyback'])
        args = urllib.urlencode(args)
        if args:
            if '?' in url: # it already has args
                url = url + "&" + args
            else:
                url = url + "?" + args
        if hash:
            url += "#" + hash
        raise Redirect(url, permanent=permanent)

    def notfound(self):
        raise NotFound()

    def forbidden(self):
        raise Forbidden()

    def get_template(self, t):
        return loader.get_template(t)

    def render_template(self, t, **kw):
        template_path = t
        if self.template_ns:
            template_path = os.path.join(self.template_ns, t)
        self.context.push()
        self.context.update(kw)
        t = self.get_template(template_path)
        result = t.render(self.context)
        self.context.pop()
        return result

    def template(self, t, **kw):
        return HttpResponse(self.render_template(t, **kw))



class BaseDispatcher(object):
    def __init__(self, handler, path=None):
        self.handler = handler
        self.path = path

    @property
    def _nr_object_path(self):
        return "%s:%s.%s" % (self.path, self.handler.__module__, self.handler.__name__)

    def __call__(self, request, path=""):
        ## instance stuff belongs in RESTLike
        instance = None
        op = ""
        rest = []

        if path.startswith("/"):
            path = path.lstrip("/")
        elements = [x for x in path.split("/") if x] # filter out blanks

        ## it can be an op or an object id
        if elements:
            if self.handler.model is not None:
                try:
                    instance = self.handler.coerce(elements[0])
                except NotFound:
                    return HttpResponseNotFound()
            if instance is None:
                op = elements[0]
                rest = elements[1:]
            elif len(elements) > 1:
                op = elements[1]
                rest = elements[2:]

        try:
            if request.method == "GET":
                return self.get(request, instance, op, rest)
            elif request.method == "POST":
                return self.post(request, instance, op, rest)
        except Redirect, e:
            if e.permanent:
                return HttpResponsePermanentRedirect(e.url)
            else:
                return HttpResponseRedirect(e.url)
        except NotFound:
            return HttpResponseNotFound()
        except Forbidden:
            return HttpResponseForbidden()
        return HttpResponseNotFound()

class FormDispatcher(BaseDispatcher):
    def get(self, request, instance=None, op="", rest=[]):
        h = self.handler(request, instance=instance, post=False, rest=rest,
                         path=self.path)

        if op and hasattr(h, "handle_" + op):
            return getattr(h, "handle_" + op)()
        return h.index()

    def post(self, request, instance=None, op="", rest=[]):
        h = self.handler(request, instance=instance, post=True, rest=rest,
                         path=self.path)

        if op and hasattr(h, "handle_" + op):
            return getattr(h, "handle_" + op)()
        return h.process()

class RESTLikeDispatcher(BaseDispatcher):
    def get(self, request, instance=None, op="", rest=[]):
        h = self.handler(request, instance=instance, post=False, rest=rest,
                         path=self.path)
        if op == "create":
            return h.create()
        elif op == "edit":
            return h.update()
        elif op and hasattr(h, "handle_" + op):
            return getattr(h, "handle_" + op)()
        elif op:
            pass # 404
        elif instance is None:
            return h.list()
        return h.view()

    def post(self, request, instance=None, op="", rest=[]):
        h = self.handler(request, instance=instance, post=True, rest=rest,
                         path=self.path)
        if op and hasattr(h, "handle_" + op):
            return getattr(h, "handle_" + op)()
        if instance is None:
            return h.create()
        return h.update()

class Resource(object):
    def __call__(self):
        return 'ok'

class APIDispatcher(RESTLikeDispatcher):
    csrf_exempt = True

    def get(self, request, instance=None, op="", rest=[]):
        return HttpResponseNotFound()

    def post(self, request, instance=None, op="", rest=[]):
        h = self.handler(request, instance=instance, post=True, rest=rest,
                         path=self.path)
        if op not in h.resources:
            return HttpResponseNotFound()
        resource = h.resources[op]()
        try:
            result = resource(self.path, rest, request)
        except NotFound:
            return HttpResponseNotFound()
        except Forbidden:
            return HttpResponseForbidden()
        return HttpResponse(result)

class FormHandler(BaseHandler):
    dispatcher = FormDispatcher

    def index(self):
        self.notfound()

    def process(self):
        self.notfound()

class RESTLikeHandler(BaseHandler):
    dispatcher = RESTLikeDispatcher

    def create(self):
        self.notfound()

    def list(self):
        self.notfound()

    def view(self):
        self.notfound()

    def update(self):
        self.notfound()

class APIHandler(BaseHandler):
    dispatcher = APIDispatcher
    csrf_exempt = True
    resources = {}

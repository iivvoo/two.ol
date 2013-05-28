from django.template import RequestContext, loader
from django.http import HttpResponse, Http404
from django.core.context_processors import csrf
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect
from django.http import HttpResponseForbidden
from django.http import HttpResponseBadRequest, HttpResponseServerError
from django.conf import settings

from django.contrib.sites.models import get_current_site

import os
import types
import urllib
import json as jsonlib
import inspect

## "Twool" / 2ol it takes two to django 
## Toolkit for Web Oriented Object Library
## 

def json(f):
    def jsonify(*args, **kw):
        return HttpResponse(jsonlib.dumps(f(*args, **kw)), mimetype="application/json")
    return jsonify

def applyrequest(f=None, **kw):
    """
        Support the following forms:
        @applyrequest
        @applyrequest()
        @applyrequest(page=int)

        by wrapping the appropriate decorator depending on wether a function
        was passed or not
    """
    if not f:
        def x(f):
            return applyrequest_notype(f, **kw)
        return x
    else:
        return applyrequest_notype(f)

def missing_args(f, args, kw):
    # http://stackoverflow.com/questions/196960/can-you-list-the-keyword-arguments-a-python-function-receives
    args, varargs, varkw, defaults = inspect.getargspec(f)
    if defaults:
        args = args[:-len(defaults)]

    return set(args).difference(kw)


## applypost, applyget, applyform?
def applyrequest_notype(f, **mapping):
    ## XXX positional arguments don't work, see reset.py -> process
    def applicator(self, *args, **kw):
        ##
        ## Improvements: figure out which arguments don't
        ## have defaults, provide proper error if missing
        request = self.request
        vars = f.func_code.co_varnames[:f.func_code.co_argcount]
        args = args[:]
        kw = kw.copy()
        for k in vars:
            try:
                v = request.REQUEST[k]
                if k in mapping:
                    v = mapping[k](v)
                kw[k] = v
            except KeyError:
                pass

        return f(self, *args, **kw)

    return applicator

def applyrequest_type(**kw):
    """
        A decorator that applies request arguments to the method,
        supporting an additional mapping. E.g.

        @applyrequest_type(page=int)
        def get(page=1):
            ...

        will get a variable 'page' from the request and convert it to int
    """
    def x(f):
        return applyrequest(f, **kw)
    return x

##
## @expose decorator that allows you to pass an entire class to 
## context, only exposing decorated methods

def context(f):
    f.contextified = True
    return f

def handler(f):
    """ identify a method as being able to handle direct calls on a 
        resource, e.g. /person/123/do_foo would map to either handle_do_foo
        or @handler def do_foo()
    """
    f.ishandler = True
    return f

## Mapping is partially mimicing django's url naming/reverse. Use that
## in stead.

from django.conf.urls import url
from django.conf.urls.defaults import patterns

def methods_for_handler(h):
    ## add callable check?
    return [x[7:] for x in dir(h) if x.startswith("handle_")] + \
           [x for x in dir(h) if getattr(x, 'ishandler', False)]  + \
           ["create", "edit"]

def Pats(path, handlerklass, name=None, **kw):
    def NewMapping(path, handlerklass, name, wp=True):
        path = path.strip("/")
        if wp:
            pathpattern = "(?P<path>(%s)*)" % "|".join(
                                       methods_for_handler(handlerklass))
        else:
            pathpattern = ""

        if path:
            pattern = "^%s/%s$" % (path, pathpattern)
        else:
            pattern = "^%s$" % pathpattern
        handler = handlerklass.dispatcher(handlerklass, path=path)
        if name:
            return url(pattern, handler, name=name, kwargs=kw)
        return url(pattern, handler, kwargs=kw)

    return patterns('',
        NewMapping(path, handlerklass, name, wp=True),
        NewMapping(path, handlerklass, name, wp=False),
    )

from django.core.urlresolvers import RegexURLResolver

def twpatterns(path, handlerklass, name=None, **kw):
    """
        Simulate an included url module with all our generated/required
        patterns

        We could (ab)use the 'prefix' part as the base part of our
        patterns, e.g.
        twpatterns('instance', '<regexppattern>', name='bla')

        Additionally, record which pattern matched during resolving
        for debugging purposes
    """
    urlpatterns = Pats(path, handlerklass, name, **kw)
    return RegexURLResolver('', urlpatterns)

def Mapping(path, handlerklass, name=None, wp=True):
    """
        The generated mappings are messy - we want to much and
        there are two somewhat conflicting systems:

        - explicit instance naming/multi model. The path contains the
          pattern, and 'path' is a possible remained (for ops / handle_*
          methods). In this case, we can restrict path to all handle_*
          methods explicitly by analyzing the handler
        - implicit. Only a base is specified; the "extracted" path is used
          for both coercing an instance and getting an op (handle_*). This
          means it can/may contan a /. E.g. /request/123/foo
          In this case, 'foo' can also be extracted from the handler.
    """
    path = path.strip("/")
    if wp:
        pathpattern = "(?P<path>.*)"
    else:
        pathpattern = ""
    if path:
        pattern = "^%s/%s$" % (path, pathpattern)
    else:
        pattern = "^%s$" % pathpattern
    handler = handlerklass.dispatcher(handlerklass, path=path)
    if name:
        return url(pattern, handler, name=name)
    return url(pattern, handler)

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

class BadRequest(BaseException):
    pass

class ServerError(BaseException):
    pass

class BaseHandler(object):
    formclass = None
    model = None
    path = '/'
    template_ns = None

    def __init__(self, request, instance=None, post=False, rest=[],
                 path=None, kw={}):
        """
            request
                The original (django) request
            instance
                A coerced instance. Can be a dictionary if the handler
                supports multiple models
            post
                True if it's a POST request
            rest
                Unresolved path components
            path
                Original path (url-pattern path?) OBSOLETE XXX
            **kw
                Arguments from the urlpattern. Also contains the instance
        """
        self.request = request
        self.context = RequestContext(request)

        self.update_context(request)

        if isinstance(instance, dict):
            self.instance = None
            ## initialize all multimodel instances to None
            if isinstance(self.model, dict):
                for k in self.model:
                    setattr(self, k, None)
            for k, v in instance.iteritems():
                setattr(self, k, v)
                self.context[k] = v
        else:
            self.instance = instance
            self.context['instance'] = self.instance
        self.post = post
        self.rest = rest
        self.path = path or self.path
        self.kw = kw

        ## instance can be a dict, depending on it in general is
        ## deprecated. Access self.instance directly, which has been
        ## unmapped
        self.verify_access(instance)

        self.messages = {}
        self.context['piggyback'] = {}

        if self.formclass:
            if post:
                if instance:
                    self.form = self.formclass(data=request.POST,
                                               instance=self.instance)
                else:
                    self.form = self.formclass(data=request.POST)
            else:
                if self.instance:
                    self.form = self.formclass(instance=self.instance)
                else:
                    self.form = self.formclass()
        else:
            self.form = None
        self.context['form'] = self.form
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
        ### XXX obsolete ?
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
        """ The piggyback can be used to store arguments that need to
            survive redirects and formposts """
        piggyback = self.context['piggyback']
        for argument in arguments:
            if argument in self.request.REQUEST:
                piggyback[argument] = self.request.REQUEST[argument]

    @classmethod
    def coerce(cls, i):
        if isinstance(cls.model, dict):
            if not isinstance(i, dict):
                i = {'instance': i}

            ## a "multi model"
            res = {}
            for (k, v) in i.iteritems():
                try:
                    res[k] = cls.model[k].objects.get(id=int(v))
                except KeyError:
                    ## ignore, it will be passed as a "kw" entry, and can
                    ## be used in create contexts, see remark below about
                    ## not able to fetch an instance
                    pass
                    # raise RuntimeError("No model defined for " + k)
                except ValueError:
                    return None
                except cls.model[k].DoesNotExist:
                    ## can't call self.notfound since we're a classmethod
                    raise NotFound()
            return res

        if isinstance(i, dict):
            ## we're handed a dict but the handler only supports a single
            ## model. Fetch the instance from the dict
            i = i.get('instance')

            ## if we were not able to fetch an instance value, there's
            ## nothing to coerce. E.g. when doing a create on
            ## POST /foo/123/bar which would create a new bar under foo 123
            if not i:
                return None

        try:
            return cls.model.objects.get(id=int(i))
        except ValueError:
            return None
        except cls.model.DoesNotExist:
            ## can't call self.notfound since we're a classmethod
            raise NotFound()

    def redirect(self, url, permanent=False, hash=None,
                 piggyback=False, **kw):
        args = kw.copy()
        if piggyback:
            args.update(self.context['piggyback'])
        ## encode args values to utf8
        encoded = {}
        for (k, v) in args.iteritems():
            if isinstance(v, unicode):
                v = v.encode('utf8')
            encoded[k] = v
        args = urllib.urlencode(encoded)
        if args:
            if '?' in url: # it already has args
                url = url + "&" + args
            else:
                url = url + "?" + args
        if hash:
            url += "#" + hash
        raise Redirect(url, permanent=permanent)

    @classmethod
    def notfound(cls):
        raise NotFound()

    @classmethod
    def forbidden(cls):
        raise Forbidden()

    @classmethod
    def badrequest(cls):
        raise BadRequest()

    @classmethod
    def servererror(cls):
        raise ServerError()

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
        return "%s:%s.%s" % (self.path, self.handler.__module__,
                             self.handler.__name__)

    def __call__(self, request, path="", **kw):
        ## instance stuff belongs in RESTLike
        instance = None
        op = ""
        rest = []

        path = path.lstrip("/")

        elements = [x for x in path.split("/") if x] # filter out blanks
        coerceable = None
        ##
        ## kw contains a mapping from the urlpattern that maps
        ## to zero or more models
        if kw:
            coerceable = kw
        elif len(elements):
            ## coerce based on the first part of the path
            coerceable = elements[0]

        ## If there's something to coerce
        if coerceable:
            if self.handler.model is not None:
                try:
                    instance = self.handler.coerce(coerceable)
                except NotFound:
                    raise Http404

            ## if it didn't result in a instance, keep the first element
            ## as part of the op / elements
            if instance is None:
                if elements:  ## might be we only have kw
                    op = elements[0]
                    rest = elements[1:]
            else:
                if kw:  ## all elements are op/rest
                    if elements:
                        op = elements[0]
                        rest = elements[1:]
                elif len(elements) > 1:  ## elements[0] was coerced
                    op = elements[1]
                    rest = elements[2:]

        try:
            if request.method == "GET":
                return self.get(request, instance, op, rest, kw=kw)
            elif request.method == "POST":
                return self.post(request, instance, op, rest, kw=kw)
        except Redirect, e:
            if e.permanent:
                return HttpResponsePermanentRedirect(e.url)
            else:
                return HttpResponseRedirect(e.url)
        except NotFound:
            raise Http404
        except Forbidden:
            return HttpResponseRedirect(settings.LOGIN_URL + "?next=" +
                                        urllib.pathname2url(request.path))
            #return HttpResponseForbidden()
        except BadRequest:
            return HttpResponseBadRequest()
        except ServerError:
            return HttpResponseServerError()

        raise Http404

    def get(self, request, instance=None, op="", rest=[], kw={}):
        pass

    def post(self, request, instance=None, op="", rest=[], kw={}):
        pass

def gethandler(h, name):
    """
        return the handler method identified by 'name'. This
        can be either 'handle_<name>', or name itself if it's
        marked as handler
    """
    if hasattr(h, "handle_" + name):
        return getattr(h, "handle_" + name)
    if hasattr(h, name):
        hh = getattr(h, name)
        if getattr(hh, "ishandler", False):
            return hh
    return None

class FormDispatcher(BaseDispatcher):
    def get(self, request, instance=None, op="", rest=[], kw={}):
        h = self.handler(request, instance=instance, post=False, rest=rest,
                         path=self.path, kw=kw)

        if op:
            hh = gethandler(h, op)
            if hh:
                return hh()
        return h.index()

    def post(self, request, instance=None, op="", rest=[], kw={}):
        h = self.handler(request, instance=instance, post=True, rest=rest,
                         path=self.path, kw=kw)

        if op:
            hh = gethandler(h, op)
            if hh:
                return hh()
        return h.process()

class RESTLikeDispatcher(BaseDispatcher):
    def get(self, request, instance=None, op="", rest=[], kw={}):
        h = self.handler(request, instance=instance, post=False, rest=rest,
                         path=self.path, kw=kw)
        if op == "create":
            return h.create()
        elif op == "edit":
            return h.update()
        elif op and gethandler(h, op):
            return gethandler(h, op)()
        elif op:
            pass # 404
        elif not instance:
            return h.list()
        elif isinstance(instance, dict) and 'instance' not in instance:
            ## "multi" model with no instance class
            return h.list()
        return h.view()

    def post(self, request, instance=None, op="", rest=[], kw={}):
        h = self.handler(request, instance=instance, post=True, rest=rest,
                         path=self.path, kw=kw)
        if op and gethandler(h, op):
            return gethandler(h, op)()
        # if not instance: -- instance may be a dict with non-instance
        if not instance or (isinstance(instance, dict) and
                            'instance' not in instance):
            return h.create()
        return h.update()

class Resource(object):
    def __call__(self):
        return 'ok'

class APIDispatcher(RESTLikeDispatcher):
    csrf_exempt = True

    def get(self, request, instance=None, op="", rest=[], kw={}):
        raise Http404

    def post(self, request, instance=None, op="", rest=[], kw={}):
        h = self.handler(request, instance=instance, post=True, rest=rest,
                         path=self.path, kw=kw)
        if op not in h.resources:
            raise Http404
        resource = h.resources[op]()
        try:
            result = resource(self.path, rest, request)
        except NotFound:
            raise Http404
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

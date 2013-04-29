def classproperty(f):
    """
        E.g.
        >>> class foo(object):
        ...    @classproperty
        ...    def name(cls):
        ...        return cls.__name__
        >>> print foo.name 
        'foo'
    """
    class name(object):
        def __init__(self, getter):  
            self.getter = getter

        def __get__(self, obj, type=None):
            return self.getter(type)
    return name(f)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

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

from django.utils.encoding import iri_to_uri
from urlparse import urljoin

def utility(request):
    """
        Add some useful niceties to the context
    """
    base_uri = "%s://%s" % (request.is_secure() and 'https' or 'http',
                            request.get_host())

    return dict(
        site_base_uri=iri_to_uri(base_uri),
        absolute_uri=iri_to_uri(urljoin(base_uri, request.get_full_path())))

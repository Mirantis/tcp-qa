import logging
import urlparse

import requests

from tcp_tests import logger

LOG = logger.logger

logger = logging.getLogger(__name__)


class HttpClient(object):
    def __init__(self, base_url=None, user=None, password=None):
        self.base_url = base_url
        self.kwargs = {}
        if user and password:
            self.kwargs.update({"auth": (user, password)})

    def set_base_url(self, base_url):
        self.base_url = base_url

    def request(self, url, method, headers=None, body=None, **kwargs):
        logger.debug(
            "Sending request to: {}, body: {}, headers: {}, kwargs: {}".format(
                url, body, headers, kwargs))
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        kwargs.update(self.kwargs)
        r = requests.request(method, urlparse.urljoin(self.base_url, url),
                             headers=headers, data=body, **kwargs)

        if not r.ok:
            raise requests.HTTPError(r.content)
        logger.debug(r.content)
        return r.headers, r.content

    def post(self, url, body=None, **kwargs):
        return self.request(url, "POST", body=body, **kwargs)

    def get(self, url, **kwargs):
        return self.request(url, "GET", **kwargs)

    def put(self, url, body=None, **kwargs):
        return self.request(url, "PUT", body=body, **kwargs)

    def delete(self, url, **kwargs):
        return self.request(url, "DELETE", **kwargs)

"""HTTP client for the supplied mock scheduler."""

import json
import logging
from time import monotonic
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class SchedulingError(Exception):
    def __init__(self, status=None):
        self.status = status


class SchedulingAPI:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    def request(self, path, *, params=None, body=None):
        method = "POST" if body is not None else "GET"
        url = self.base_url + path
        if params:
            url += "?" + urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        request = Request(url, data=data, method=method,
                          headers={"Content-Type": "application/json"})
        start = monotonic()
        status = None
        try:
            with urlopen(request, timeout=5) as response:
                status = response.status
                result = json.load(response)
                if not isinstance(result, dict):
                    raise SchedulingError()
                return result
        except HTTPError as error:
            status = error.code
            error.close()
            raise SchedulingError(status) from None
        except (URLError, OSError, ValueError):
            raise SchedulingError() from None
        finally:
            logging.info("%s %s status=%s elapsed_ms=%.1f",
                         method, path, status, (monotonic() - start) * 1000)

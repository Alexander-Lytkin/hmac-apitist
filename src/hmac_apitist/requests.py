import inspect
from abc import ABC
from typing import List, Type, TypeVar, Union
from hmac_apitist.hmac_req import CanonicalRequest

from requests import PreparedRequest, Request, Response
from requests import Session as OldSession

from hmac_apitist.logging import Logging


class SessionHook(ABC):
    pass


class RequestHook(SessionHook):
    def run(self, request: Request) -> Request:
        ...


class PreparedRequestHook(SessionHook):
    def run(self, request: PreparedRequest) -> PreparedRequest:
        ...


class ResponseHook(SessionHook):
    def run(self, response: Response) -> Response:
        ...


DataType = TypeVar("DataType")


class ApitistResponse(Response):
    data: DataType

    def __init__(self, response: Response):
        self.__dict__ = response.__dict__

    def verify_response(
            self, ok_status: Union[int, List[int]] = 200
    ) -> "ApitistResponse":
        func = inspect.stack()[2][3]
        if isinstance(ok_status, int):
            ok_status = [ok_status]
        if self.status_code not in ok_status:
            raise ValueError(
                f"Verified response: function {func} failed: "
                f"server responded {self.status_code} "
                f"with data: {self.content}"
            )
        else:
            Logging.logger.info(
                f"Verified response: function {func} code {self.status_code}"
            )
        return self

    def vr(self, ok_status: Union[int, List[int]] = 200) -> "ApitistResponse":
        return self.verify_response(ok_status=ok_status)

    def structure(self, t: Type[DataType]) -> "ApitistResponse":
        ...


class Session(OldSession):
    def __init__(self):
        super().__init__()
        self.request_hooks = []
        self.prep_request_hooks = []
        self.response_hooks = []
        self.is_hmac = True
        self.hmac_key = None
        self.hmac_path_replacer = None

    def _add_hook(
            self,
            hook: Type[Union[RequestHook, PreparedRequestHook, ResponseHook]],
            array: list,
    ):
        array.append(hook)

    def add_request_hook(self, hook: Type[RequestHook]):
        Logging.logger.debug("Adding new request hook")
        self._add_hook(hook, self.request_hooks)

    def add_prep_request_hook(self, hook: Type[PreparedRequestHook]):
        Logging.logger.debug("Adding new prepared request hook")
        self._add_hook(hook, self.prep_request_hooks)

    def add_response_hook(self, hook: Type[ResponseHook]):
        Logging.logger.debug("Adding new response hook")
        self._add_hook(hook, self.response_hooks)

    def add_hook(
            self, hook: Type[Union[RequestHook, PreparedRequestHook, ResponseHook]]
    ):
        if issubclass(hook, RequestHook):
            self.add_request_hook(hook)
        elif issubclass(hook, PreparedRequestHook):
            self.add_prep_request_hook(hook)
        elif issubclass(hook, ResponseHook):
            self.add_response_hook(hook)

    def _run_hooks(
            self,
            array: List[
                Type[Union[RequestHook, PreparedRequestHook, ResponseHook]]
            ],
            data: Union[Request, PreparedRequest, Response, ApitistResponse],
    ):
        for hook in array:
            data = hook().run(data)
        return data

    def request(
            self,
            method,
            url,
            params=None,
            data=None,
            headers=None,
            cookies=None,
            files=None,
            auth=None,
            timeout=None,
            allow_redirects=True,
            proxies=None,
            hooks=None,
            stream=None,
            verify=None,
            cert=None,
            json=None,
    ) -> ApitistResponse:
        """Constructs a :class:`Request <Request>`, prepares it and sends it.
        Returns :class:`Response <Response>` object.

        :param method: method for the new :class:`Request` object.
        :param url: URL for the new :class:`Request` object.
        :param params: (optional) Dictionary or bytes to be sent in the query
            string for the :class:`Request`.
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param json: (optional) json to send in the body of the
            :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the
            :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the
            :class:`Request`.
        :param files: (optional) Dictionary of ``'filename':
            file-like-objects`` for multipart encoding upload.
        :param auth: (optional) Auth tuple or callable to enable
            Basic/Digest/Custom HTTP Auth.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :type timeout: float or tuple
        :param allow_redirects: (optional) Set to True by default.
        :type allow_redirects: bool
        :param proxies: (optional) Dictionary mapping protocol or protocol and
            hostname to the URL of the proxy.
        :param stream: (optional) whether to immediately download the response
            content. Defaults to ``False``.
        :param verify: (optional) Either a boolean, in which case it controls
            whether we verify the server's TLS certificate, or a string,
            in which case it must be a path to a CA bundle to use.
            Defaults to ``True``.
        :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair.
        :rtype: requests.Response
        """
        # Create the Request.

        req = Request(
            method=method.upper(),
            url=url,
            headers=headers,
            files=files,
            data=data,
            json=json,
            params=params or {},
            auth=auth,
            cookies=cookies,
            hooks=hooks,
        )
        req = self._run_hooks(self.request_hooks, req)
        prep = self.prepare_request(req)
        if self.is_hmac and self.hmac_key is not None:
            cr = CanonicalRequest(prep, self.hmac_key, self.hmac_path_replacer)
            prep.headers.update(cr.get_headers_for_hmac())

        prep = self._run_hooks(self.prep_request_hooks, prep)

        proxies = proxies or {}

        settings = self.merge_environment_settings(
            prep.url, proxies, stream, verify, cert
        )

        # Send the request.
        send_kwargs = {"timeout": timeout, "allow_redirects": allow_redirects}
        send_kwargs.update(settings)
        resp = ApitistResponse(self.send(prep, **send_kwargs))
        resp = self._run_hooks(self.response_hooks, resp)

        return resp


def session():
    """
    Returns a :class:`Session` for context-management.

    :rtype: Session
    """
    return Session()

from ast import Dict
from typing import Optional

from requests import Response, Session

from .base import AbstractClient
from .base import ResponseWrapper as BaseResponse


class ResponseWrapper(BaseResponse):
    raw: Response

    def __init__(self, raw: Response):
        self.raw = raw
        self.status = raw.status_code
        self.headers = raw.headers

    def json(self):
        return self.raw.json()

    @property
    def text(self):
        return self.raw.text


class RequestsSession(AbstractClient):
    session: Session

    def __init__(self, instance: Optional[Session] = None):
        self.session = instance or Session()

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> ResponseWrapper:
        response = self.session.request(
            method=method, url=url, headers=headers, data=data
        )
        return ResponseWrapper(response)

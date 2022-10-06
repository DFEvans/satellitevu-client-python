from importlib import import_module
from json import dumps
from unittest.mock import Mock

from mocket import Mocket, Mocketizer
from mocket.mockhttp import Entry
from pytest import fixture, mark, param, skip

from satellitevu.auth.auth import Auth

from . import ResponseWrapper, UrllibClient

try:
    from requests import Session as RequestsSession
except ImportError:
    RequestsSession = None
try:
    from httpx import Client as HttpxClient
except ImportError:
    HttpxClient = None


@fixture(
    params=(
        param("UrllibClient"),
        param(
            "requests.RequestsSession",
            marks=[
                mark.skipif(RequestsSession is None, reason="requests is not installed")
            ],
        ),
        param(
            "HttpxClient",
            marks=[mark.skipif(HttpxClient is None, reason="httpx is not installed")],
        ),
    )
)
def http_client_class(request):
    full_path = f"{__package__}.{request.param}"
    module = import_module(full_path.rsplit(".", maxsplit=1)[0])
    return getattr(module, full_path.rsplit(".")[-1])


@mark.parametrize("method", ("GET", "POST"))
def test_http_client(http_client_class, method):
    client = http_client_class()

    Entry.single_register(
        method, "http://example.com/", body=dumps({"message": "Hello"})
    )
    with Mocketizer():
        response = client.request(method, "http://example.com/")

    assert isinstance(response, ResponseWrapper)
    assert response.json() == {"message": "Hello"}


def test_http_custom_actor(http_client_class):
    if http_client_class == UrllibClient:
        skip("UrllibClient does not support custom instance")

    instance = Mock()
    client = http_client_class(instance=instance)
    client.request("GET", "http://example.com/")

    assert instance.request.called


@mark.parametrize(
    "url, headers, uses_injected_auth",
    (
        ("http://example.com/", None, False),
        ("http://api.example.com/", None, False),
        ("http://api.example.com/non-authed", None, False),
        ("http://api.example.com/authed/", None, True),
        ("http://api.example.com/authed/subpath", None, True),
        (
            "http://api.example.com/authed/subpath",
            {"Authorization": "some-other"},
            False,
        ),
    ),
)
def test_http_set_auth(http_client_class, url, headers, uses_injected_auth):
    auth = Mock(wraps=Auth(client_id="mocked", client_secret="mocked"))
    auth.token.return_value = "mock-token"
    Entry.single_register("GET", url)

    client = http_client_class()
    client.set_auth("http://api.example.com/authed/", auth)

    with Mocketizer():
        client.request("GET", url, headers=headers)
        requests = Mocket.request_list()

    assert len(requests) == 1
    assert (
        requests[0].headers.get("Authorization") == "mock-token"
    ) == uses_injected_auth


@mark.parametrize(
    "data, json, body, content_type",
    (
        ({"foo": "bar"}, None, "foo=bar", "application/x-www-form-urlencoded"),
        (None, {"foo": "bar"}, '{"foo": "bar"}', "application/json"),
        (
            {"bar": "foo"},
            {"foo": "bar"},
            "bar=foo",
            "application/x-www-form-urlencoded",
        ),
    ),
)
def test_payload(http_client_class, data, json, body, content_type):
    client = http_client_class()
    Entry.single_register("POST", "http://api.example.com")

    with Mocketizer():
        client.request("POST", "http://api.example.com", data=data, json=json)
        request = Mocket.last_request()
    assert request.headers["Content-Type"] == content_type
    assert request.body == body

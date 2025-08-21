import json
import pytest

from scan2epub.translate.translator import AzureTranslator
from scan2epub.utils.errors import TranslationError


class _MockResp:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        if self._json is None:
            raise ValueError("No JSON")
        return self._json


class _MockSession:
    def __init__(self, responses):
        """
        responses: iterable of _MockResp to return per post() call
        """
        self._responses = list(responses)
        self.posts = []
        self.post_calls = 0
        self.last_headers = None
        self.last_url = None
        self.last_params = None
        self.last_json = None

    def post(self, url, params=None, json=None, headers=None, timeout=None):
        self.post_calls += 1
        self.posts.append((url, params, json, headers, timeout))
        self.last_headers = headers
        self.last_url = url
        self.last_params = params
        self.last_json = json
        if not self._responses:
            raise AssertionError("No more mock responses queued")
        return self._responses.pop(0)


def test_preflight_success_single_call():
    sess = _MockSession([
        _MockResp(200, json_data=[{"translations": [{"text": "pong"}]}])
    ])
    tr = AzureTranslator(
        endpoint="https://api.cognitive.microsofttranslator.com",
        api_key="dummy",
        region=None,
        api_version="3.0",
        session=sess,
        timeout_s=5,
    )
    tr.preflight_check("en")
    assert sess.post_calls == 1, "Preflight must do exactly one network call"


def test_preflight_http_404_raises_and_single_call():
    sess = _MockSession([
        _MockResp(404, json_data={"error": {"code": "NotFound"}}, text='{"error":{"code":"NotFound"}}')
    ])
    tr = AzureTranslator(
        endpoint="https://api.cognitive.microsofttranslator.com",
        api_key="dummy",
        region=None,
        api_version="3.0",
        session=sess,
        timeout_s=5,
    )
    with pytest.raises(TranslationError):
        tr.preflight_check("en")
    assert sess.post_calls == 1


def test_preflight_unexpected_shape_raises():
    sess = _MockSession([
        _MockResp(200, json_data={"not": "a-list"})
    ])
    tr = AzureTranslator(
        endpoint="https://api.cognitive.microsofttranslator.com",
        api_key="dummy",
        region=None,
        api_version="3.0",
        session=sess,
        timeout_s=5,
    )
    with pytest.raises(TranslationError):
        tr.preflight_check("en")
    assert sess.post_calls == 1


def test_preflight_includes_region_header_when_provided():
    sess = _MockSession([
        _MockResp(200, json_data=[{"translations": [{"text": "pong"}]}])
    ])
    tr = AzureTranslator(
        endpoint="https://api.cognitive.microsofttranslator.com",
        api_key="dummy",
        region="westeurope",
        api_version="3.0",
        session=sess,
        timeout_s=5,
    )
    tr.preflight_check("de")
    assert sess.post_calls == 1
    assert sess.last_headers.get("Ocp-Apim-Subscription-Region") == "westeurope"
    assert sess.last_params.get("to") == "de"
    # body must be tiny ping
    assert isinstance(sess.last_json, list) and sess.last_json[0].get("Text") == "ping"

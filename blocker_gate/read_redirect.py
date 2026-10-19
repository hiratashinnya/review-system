"""読み取り専用transportだけに適用するredirect送信境界。"""

from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, build_opener

from .read_request_policy import read_headers, validate_rest_get


class ReadRedirectHandler(HTTPRedirectHandler):
    """標準のmethod変換後、次のI/Oより前に読み取り境界を再検査する。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
            if redirected.get_method() != "GET":
                raise ValueError("Only repository REST GET redirects are permitted")
            validate_rest_get(redirected.full_url)
            read_headers(dict(redirected.header_items()), graphql=False)
        except ValueError as exc:
            raise HTTPError(req.full_url, code, "Unsafe read redirect", headers, fp) from exc
        return redirected

    def http_error_302(self, req, fp, code, msg, headers):
        try:
            return super().http_error_302(req, fp, code, msg, headers)
        except ValueError as exc:
            raise HTTPError(req.full_url, code, "Invalid read redirect", headers, fp) from exc

    http_error_301 = http_error_303 = http_error_307 = http_error_308 = http_error_302


def urlopen(request, *, timeout):
    """プロセス共通openerを変更せず、各redirectへ局所policyを適用する。"""
    return build_opener(ReadRedirectHandler()).open(request, timeout=timeout)

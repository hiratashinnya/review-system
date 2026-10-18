"""実ネットワークを使わずurllibのredirect処理だけを通すfixture。"""

import io
from email.message import Message
from urllib.request import BaseHandler
from urllib.response import addinfourl


class MemoryNetwork(BaseHandler):
    handler_order = 100

    def __init__(self, redirects):
        self.redirects = redirects
        self.seen = []

    def https_open(self, request):
        return self.respond(request)

    def http_open(self, request):
        return self.respond(request)

    def respond(self, request):
        self.seen.append((request.full_url, request.get_method(), request.get_header("Authorization")))
        headers = Message()
        index = len(self.seen) - 1
        status = 200
        if index < len(self.redirects):
            status, headers["Location"] = self.redirects[index]
        response = addinfourl(io.BytesIO(b"{}"), headers, request.full_url, status)
        response.msg = "Found" if status != 200 else "OK"
        return response

import json

from tcp_tests.managers.clients import http_client


class PrometheusClient(object):
    def __init__(self, host, port,proto):
        self.url = '{0}{1}{2}'.format(proto, host, port)
        self.client = http_client.HttpClient(base_url=self.url)

    def get_targets(self):
        resp = self.client.get("/api/v1/targets")
        targets = json.loads(resp)
        return targets["data"]["activeTargets"]

    def get_query(self, query, timestamp=None):
        params = {
            "query": query
        }

        if timestamp is not None:
            params.update({"time": timestamp})

        _, resp = self.client.get("/api/v1/query", params=params)

        query_result = json.loads(resp)
        if query_result["status"] != "success":
            raise Exception("Failed resp: {}".format(resp))

        if query_result["data"]["resultType"] == "vector":
            return query_result["data"]["result"]

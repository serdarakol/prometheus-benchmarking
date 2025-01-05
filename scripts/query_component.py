import requests
import time
import json
import os

PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://localhost:9090/api/v1/query")
QUERY_LIST = os.environ.get("QUERY_LIST", '["rate(metric_0[1m])"]')
LOG_FILE = os.environ.get("LOG_FILE", "query_logs.json")
QUERY_INTERVAL = os.environ.get("INTERVAL", 10)
EXPERIMENT_DURATION = os.environ.get("DURATION", 60)

class QueryComponent:
    def __init__(self):
        self.queries = QUERY_LIST
        self.interval = QUERY_INTERVAL
        self.duration = EXPERIMENT_DURATION
        self.log_file = LOG_FILE

    def execute_query(self, query):
        response = requests.get(PROMETHEUS_URL, params={"query": query})
        result = {
            "query": query,
            "timestamp": time.time(),
            "status_code": response.status_code
        }
        if response.status_code == 200:
            result["latency_ms"] = response.elapsed.total_seconds() * 1000
            result["data"] = response.json()
            result["elapsed"] = response.elapsed
        return result

    def run(self):
        start_time = time.time()
        logs = []
        while time.time() - start_time < self.duration:
            for query in self.queries:
                logs.append(self.execute_query(query))
                time.sleep(self.interval)
        with open(self.log_file, 'w') as f:
            json.dump(logs, f, indent=4)

if __name__ == "__main__":
    component = QueryComponent()
    component.run()
    print("Query execution completed.")

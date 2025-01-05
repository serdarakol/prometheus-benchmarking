import requests
import time
import json
import os
import random


# Environment variables
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://localhost:9090/api/v1/query")
QUERY_LIST = json.loads(os.environ.get("QUERY_LIST", '["rate(metric_0[1m])"]'))
LOG_FILE = os.environ.get("LOG_FILE", "query_logs.json")
QUERY_INTERVAL = int(os.environ.get("QUERY_INTERVAL", 10))
EXPERIMENT_DURATION = int(os.environ.get("EXPERIMENT_DURATION", 60))
SEED = int(os.environ.get("SEED", 42))

random.seed(SEED)

class QueryComponent:
    def __init__(self):
        self.queries = QUERY_LIST
        self.interval = QUERY_INTERVAL
        self.duration = EXPERIMENT_DURATION
        self.log_file = LOG_FILE

    def execute_query(self, query):
        t0 = int(time.time() * 1000)
        try:
            response = requests.get(PROMETHEUS_URL, params={"query": query}, timeout=10)
            t1 = int(time.time() * 1000)
            latency_ms = response.elapsed.total_seconds() * 1000
            result = {
                "query": query,
                "request_timestamp_ms": t0,
                "respond_timestamp_ms": t1,
                "status_code": response.status_code,
                "latency_ms": latency_ms
            }
            if response.status_code == 200:
                result["data"] = response.json()
            else:
                result["error"] = f"Non-200 response: {response.status_code}"
        except requests.exceptions.RequestException as e:
            t1 = int(time.time() * 1000)
            result = {
                "query": query,
                "request_timestamp_ms": t0,
                "respond_timestamp_ms": t1,
                "status_code": None,
                "latency_ms": None,
                "error": str(e)
            }
        return result

    def run(self):
        start_time = time.time()
        logs = []

        while time.time() - start_time < self.duration:
            query = random.choice(self.queries)
            logs.append(self.execute_query(query))
            time.sleep(self.interval)

        # Write logs to file
        with open(self.log_file, 'w') as f:
            json.dump(logs, f, indent=4)

if __name__ == "__main__":
    component = QueryComponent()
    component.run()
    print("Query execution completed.")

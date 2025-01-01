import requests
import time
import json

PROMETHEUS_URL = f'http://<PROMETHEUS_IP>:9090/api/v1/query'

class QueryComponent:
    def __init__(self, queries, interval, duration, log_file):
        self.queries = queries
        self.interval = interval
        self.duration = duration
        self.log_file = log_file

    def execute_query(self, query):
        response = requests.get(PROMETHEUS_URL, params={"query": query})
        result = {
            "query": query,
            "timestamp": time.time(),
            "status_code": response.status_code
        }
        if response.status_code == 200:
            result["latency"] = response.elapsed.total_seconds()
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
    queries = ["rate(metric_0[1m])", "avg_over_time(metric_1[5m])"]
    component = QueryComponent(queries, interval=10, duration=300, log_file="query_logs.json")
    component.run()
    print("Query execution completed.")

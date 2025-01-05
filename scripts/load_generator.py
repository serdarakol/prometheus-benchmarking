from prometheus_client import Gauge, CollectorRegistry, generate_latest
import random
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

START_PORT = os.environ.get("STARTING_PORT", 8000)
NUM_TARGETS = os.environ.get("NUM_TARGETS", 5)
class MetricHandler(BaseHTTPRequestHandler):
    def __init__(self, registry, *args, **kwargs):
        self.registry = registry
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header("Content-type", "text/plain; version=0.0.4; charset=utf-8")
            self.end_headers()
            self.wfile.write(generate_latest(self.registry))
        else:
            self.send_response(404)
            self.end_headers()


class ScrapeTarget:
    def __init__(self, port, metric_name):
        self.registry = CollectorRegistry()
        self.metric = Gauge(metric_name, f"Metric for {metric_name}", registry=self.registry)
        self.port = port

    def start(self):
        def run_server():
            server = HTTPServer(('localhost', self.port), lambda *args, **kwargs: MetricHandler(self.registry, *args, **kwargs))
            server.serve_forever()

        threading.Thread(target=run_server, daemon=True).start()

        while True:
            self.metric.set(random.uniform(0, 100))
            time.sleep(1)


class LoadGenerator:
    def __init__(self):
        self.start_port = START_PORT
        self.num_targets = NUM_TARGETS
        self.targets = []

    def run(self):
        for i in range(self.num_targets):
            port = self.start_port + i
            metric_name = f"metric_{i}"
            target = ScrapeTarget(port, metric_name)
            self.targets.append(target)
            threading.Thread(target=target.start, daemon=True).start()


if __name__ == "__main__":
    generator = LoadGenerator()
    generator.run()
    print("Load generators running with isolated metrics per target...")
    while True:
        time.sleep(10)

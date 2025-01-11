from prometheus_client import Gauge, CollectorRegistry, generate_latest
import random
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import logging

# Environment variables
LOG_FILE = os.environ.get("LOG_FILE", "load_generator.log")
START_PORT = int(os.environ.get("START_PORT", 8000))
NUM_TARGETS = int(os.environ.get("NUM_TARGETS", 5))
SEED = int(os.environ.get("SEED", 42))

# Configure logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

random.seed(SEED)

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
        """Starts the scrape target server and updates metrics continuously."""
        def run_server():
            server = HTTPServer(('0.0.0.0', self.port), lambda *args, **kwargs: MetricHandler(self.registry, *args, **kwargs))
            server.serve_forever()

        # Start the HTTP server
        threading.Thread(target=run_server, daemon=True).start()

        # Update metrics continuously
        while True:
            value = random.uniform(0, 100)
            self.metric.set(value)
            logging.info(f"{int(time.time() * 1000)} - Metric updated: port={self.port}, metric={self.metric._name}, value={value:.2f}")
            time.sleep(1)

class LoadGenerator:
    def __init__(self):
        self.start_port = START_PORT
        self.num_targets = NUM_TARGETS
        self.targets = []
        logging.info(f"Load generator started with {self.num_targets} targets, starting at port {self.start_port}.")

    def run(self):
        threads = []

        # Start scrape targets
        for i in range(self.num_targets):
            port = self.start_port + i
            metric_name = f"metric_{i}"
            target = ScrapeTarget(port, metric_name)
            self.targets.append(target)
            thread = threading.Thread(target=target.start, daemon=True)
            threads.append(thread)
            thread.start()

        # Keep the main thread alive
        while True:
            time.sleep(1)


if __name__ == "__main__":
    generator = LoadGenerator()
    try:
        generator.run()
    except KeyboardInterrupt:
        logging.info("Load generator interrupted. Exiting.")

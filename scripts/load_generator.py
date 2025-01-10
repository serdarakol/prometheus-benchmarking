from prometheus_client import Gauge, CollectorRegistry, generate_latest
import random
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import logging
from google.cloud import storage

# Environment variables
LOG_FILE = os.environ.get("LOG_FILE", "load_generator.log")
START_PORT = int(os.environ.get("START_PORT", 8000))
NUM_TARGETS = int(os.environ.get("NUM_TARGETS", 5))
SEED = int(os.environ.get("SEED", 42))
EXPERIMENT_DURATION = int(os.environ.get("EXPERIMENT_DURATION", 60))
EXPERIMENT_ID = os.environ.get("EXPERIMENT_ID", "default")


GCS_BUCKET_NAME='prometheus-benchmarking-app-logs'
GCS_FILE_NAME=f'{EXPERIMENT_ID}/load_generator_logs/{LOG_FILE}'

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

    def start(self, experiment_duration):
        def run_server():
            server = HTTPServer(('0.0.0.0', self.port), lambda *args, **kwargs: MetricHandler(self.registry, *args, **kwargs))
            server.serve_forever()

        threading.Thread(target=run_server, daemon=True).start()
        start_time = time.time()

        while time.time() - start_time < experiment_duration:
            value = random.uniform(0, 100)
            self.metric.set(value)
            logging.info(f"{int(time.time() * 1000)} - Metric updated: port={self.port}, metric={self.metric._name}, value={value:.2f}")
            time.sleep(1)

class LoadGenerator:
    def __init__(self):
        self.start_port = START_PORT
        self.num_targets = NUM_TARGETS
        self.targets = []
        self.experiment_duration = EXPERIMENT_DURATION
        logging.info(f"Load generator started with {self.num_targets} targets, starting at port {self.start_port}.")

    def upload_log_to_gcs(self):
        """Uploads the log file to Google Cloud Storage."""
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(GCS_FILE_NAME)

        # Upload the log file
        blob.upload_from_filename(LOG_FILE)

    def run(self):
        threads = []

        for i in range(self.num_targets):
            port = self.start_port + i
            metric_name = f"metric_{i}"
            target = ScrapeTarget(port, metric_name)
            self.targets.append(target)
            thread = threading.Thread(target=target.start, args=(self.experiment_duration,), daemon=True)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete the experiment duration
        for thread in threads:
            thread.join()

        # Upload log file to GCS
        self.upload_log_to_gcs()

if __name__ == "__main__":
    generator = LoadGenerator()
    generator.run()
    logging.info("Load generator experiment completed.")

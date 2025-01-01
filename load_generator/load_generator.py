from prometheus_client import start_http_server, Gauge
import random
import time
import threading

class LoadGenerator:
    def __init__(self, start_port, num_targets):
        self.start_port = start_port
        self.num_targets = num_targets
        self.targets = []

    def create_target(self, port, metric_name):
        metric = Gauge(metric_name, f"Metric for {metric_name}")
        start_http_server(port)

        def update_metric():
            while True:
                value = random.uniform(0, 100)
                metric.set(value)
                time.sleep(1)  # Update every second

        threading.Thread(target=update_metric, daemon=True).start()

    def run(self):
        for i in range(self.num_targets):
            port = self.start_port + i
            metric_name = f"metric_{i}"
            self.create_target(port, metric_name)

if __name__ == "__main__":
    generator = LoadGenerator(start_port=8000, num_targets=5)
    generator.run()
    print("Load generators running...")
    while True:
        time.sleep(10)

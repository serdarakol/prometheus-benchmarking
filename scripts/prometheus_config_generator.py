import yaml
import os
import json

def generate_prometheus_config(targets, scrape_interval, prometheus_instances, federation=False):

    config = {
        "global": {"scrape_interval": scrape_interval},
        "scrape_configs": [
            {
                "job_name": "load_generators",
                "static_configs": [{"targets": targets}]
            },
            {
                "job_name": "self",
                "static_configs": [{"targets": ["localhost:9090"]}]
            }
        ]
    }

    if federation and prometheus_instances:
        config["scrape_configs"].append({
            "job_name": "federation",
            "metrics_path": "/federate",
            "params": {
                "match[]": ["{job=\"load_generators\"}", "{job=\"self\"}"]
            },
            "static_configs": [{"targets": prometheus_instances}]
        })

    return config

if __name__ == "__main__":

    targets = json.loads(os.environ.get("SCRAPE_TARGETS", '[]'))
    prometheus_instances = json.loads(os.environ.get("PROMETHEUS_INSTANCES", '[]'))
    scrape_interval = os.environ.get("SCRAPE_INTERVAL", "5s")
    federation_enabled = os.environ.get("FEDERATION", "false").lower() == "true"

    config = generate_prometheus_config(targets, scrape_interval, prometheus_instances, federation_enabled)

    config_path = os.environ.get("PROMETHEUS_CONFIG_PATH", "./prometheus.yml")
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

    print(f"Prometheus configuration generated at {config_path}")

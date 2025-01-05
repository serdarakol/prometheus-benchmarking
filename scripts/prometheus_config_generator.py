import yaml

def generate_prometheus_config(targets, scrape_interval="5s"):
    config = {
        "global": {"scrape_interval": scrape_interval},
        "scrape_configs": []
    }
    for i, target in enumerate(targets):
        job_name = f"load_generator_{i}"
        config["scrape_configs"].append({
            "job_name": job_name,
            "static_configs": [{"targets": [target]}]
        })
    return config

if __name__ == "__main__":
    targets = [f"localhost:{8000 + i}" for i in range(5)]
    config = generate_prometheus_config(targets)
    with open("prometheus_component/prometheus.yml", 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    print("Prometheus configuration generated.")

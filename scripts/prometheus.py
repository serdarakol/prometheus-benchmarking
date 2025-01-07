import yaml
import subprocess
import os

def generate_prometheus_config(scrape_targets, scrape_interval, is_leaf):
    config = {
        "global": {
            "scrape_interval": scrape_interval
        },
        "scrape_configs": []
    }

    if is_leaf:
        # Leaf instance scraping load generators
        config["scrape_configs"].append({
            "job_name": "load_generators",
            "static_configs": [{"targets": scrape_targets}]
        })
    else:
        # Central instance scraping leaf Prometheus instances
        config["scrape_configs"].append({
            "job_name": "leaf_prometheus",
            "metrics_path": "/federate",
            "params": {
                "match[]": ["{job=\"load_generators\"}"]
            },
            "static_configs": [{"targets": scrape_targets}]
        })

    return config


def upload_config(ip, config):
    config_path = "/etc/prometheus/prometheus.yml"
    temp_file = f"./prometheus_{ip.replace('.', '_')}.yml"

    with open(temp_file, "w") as f:
        yaml.dump(config, f)

    subprocess.run(["scp", temp_file, f"user@{ip}:{config_path}"])

    restart_script = f"""
    sudo systemctl restart prometheus
    """
    subprocess.run(["ssh", f"user@{ip}", restart_script])

    # os.remove(temp_file)

import yaml
import subprocess
import os
import time
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


def upload_config(vm_name, zone, project_id, config):
    # Created a temporary file for the Prometheus config
    tmp_dir = "tmp"
    os.makedirs(tmp_dir, exist_ok=True)  # Create the tmp directory if it doesn't exist

    temp_file = f"tmp/{vm_name.replace('.', '_')}.yml"
    with open(temp_file, "w") as f:
        yaml.dump(config, f)

    # Path to store the config file on the VM
    remote_path = "prometheus.yml"

    # Upload the config file to the VM using gcloud compute scp
    subprocess.run(
        [
            "gcloud", "compute", "scp", temp_file,
            f"{vm_name}:{remote_path}",
            "--zone", zone,
            "--project", project_id,
        ],
        check=True,
    )
    print(f"Uploaded {temp_file} to {vm_name}:{remote_path}")

    # SSH into the VM to move the config file and restart Prometheus
    wait_for_startup(vm_name, zone, project_id)
    ssh_command = f"""
    sudo systemctl restart prometheus
    """
    subprocess.run(
        [
            "gcloud", "compute", "ssh", vm_name,
            "--zone", zone,
            "--project", project_id,
            "--command", ssh_command,
        ],
        check=True,
    )
    print(f"Prometheus on {vm_name} restarted with the new configuration.")

    # os.remove(temp_file)
    # print(f"Temporary file {temp_file} removed.")


def wait_for_startup(vm_name, zone, project_id):
    while True:
        result = subprocess.run(
            [
                "gcloud", "compute", "ssh", vm_name,
                "--zone", zone,
                "--project", project_id,
                "--command", "test -f /tmp/startup_ready && echo READY || echo NOT_READY"
            ],
            capture_output=True, text=True
        )
        if "READY" in result.stdout:
            print(f"{vm_name} is ready.")
            break
        time.sleep(10)  # Check again in 10 seconds

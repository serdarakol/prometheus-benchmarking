import yaml
import subprocess
from helpers import wait_for_startup


def initialize_prometheus(prometheus_VMs, load_generator_server_ips, load_generator_envs, scrape_interval, zone, project_id, log_path):
    ## distribute load generators among prometheus instances and flatten the list
    def distribute_targets_evenly(targets_list, num_chunks):
        # First, flatten the list of lists.
        all_targets = [url for sublist in targets_list for url in sublist]
        n = len(all_targets)
        chunks = []
        # Determine the base chunk size and how many chunks need an extra element.
        base_size = n // num_chunks
        remainder = n % num_chunks
        start = 0
        for i in range(num_chunks):
            # The first 'remainder' chunks get one extra target.
            chunk_size = base_size + (1 if i < remainder else 0)
            chunks.append(all_targets[start:start + chunk_size])
            start += chunk_size
        return chunks
    central_instance = prometheus_VMs[0]
    leaf_instances = prometheus_VMs[1:]

    # Generate new scrape targets for load generators
    new_scrape_targets = []  ## [[url1, url2, url3], [url4, url5, url6], ...]
    for i, target in enumerate(load_generator_server_ips):
        env_vars = load_generator_envs[i]
        new_urls = [f"{target}:{env_vars['START_PORT'] + j}" for j in range(env_vars["NUM_TARGETS"])]
        new_scrape_targets.append(new_urls)

    # If 1 prometheus instance, it scrapes everything
    if not leaf_instances:
        all_targets = [url for sublist in new_scrape_targets for url in sublist] # flattened
        central_config = generate_prometheus_config(all_targets, scrape_interval, is_leaf=True)
        upload_config(central_instance, zone, project_id, central_config, log_path)
        return

    # number of prometheus instances can be 1, 3 or more. for 2, no federation and no benchmarking
    distributed_targets = distribute_targets_evenly(new_scrape_targets, len(leaf_instances))
    for leaf_ip, leaf_targets in zip(leaf_instances, distributed_targets):
        leaf_config = generate_prometheus_config(leaf_targets, scrape_interval, is_leaf=True)
        upload_config(leaf_ip, zone, project_id, leaf_config, log_path)


    # Central instance scrapes all leaf instances
    leaf_urls = [f"{ip}:9090" for ip in leaf_instances]
    central_config = generate_prometheus_config(leaf_urls, scrape_interval, is_leaf=False)
    upload_config(central_instance, zone, project_id, central_config, log_path)


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


def upload_config(vm_name, zone, project_id, config, log_path):

    temp_file = f"{log_path}/prometheus_configs/{vm_name}.yml"
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
    ssh_command = (
        f"sudo systemctl stop prometheus && "
        f"sudo -u prometheus prometheus --config.file={remote_path} "
    )
    subprocess.Popen(
        [
            "gcloud", "compute", "ssh", vm_name,
            "--zone", zone,
            "--project", project_id,
            "--command", ssh_command,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    print(f"Prometheus on {vm_name} restarted with the new configuration.")

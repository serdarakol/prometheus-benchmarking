import subprocess
import json
import time
import os
from .prometheus import generate_prometheus_config, upload_config


def run_terraform(action, variables=None):
    if variables:
        with open("terraform/terraform.tfvars", "w") as f:
            for key, value in variables.items():
                f.write(f"{key} = {json.dumps(value)}\n")
    subprocess.run(["terraform", action, "-auto-approve"])


def get_terraform_output(output_name):
    result = subprocess.run(["terraform", "output", "-json", output_name], capture_output=True, text=True)
    return json.loads(result.stdout)


def initialize_load_generators(load_generator_ips, env_vars):
    for i, ip in enumerate(load_generator_ips):
        script = f"""
        export START_PORT={env_vars["START_PORT"]}
        export NUM_TARGETS={env_vars["NUM_TARGETS"]}
        export SEED={env_vars["SEED"]}
        export LOG_FILE=/var/log/load_generator_{i}.log

        sudo apt-get update
        sudo apt-get install -y python3-pip
        pip3 install prometheus_client
        python3 /path/to/load_generator.py
        """
        subprocess.run(["ssh", f"user@{ip}", script])


def initialize_prometheus(prometheus_ips, scrape_targets, scrape_interval):
    central_instance = prometheus_ips.pop(0)
    leaf_instances = prometheus_ips

    # Configure leaf Prometheus instances
    for i, ip in enumerate(leaf_instances):
        config = generate_prometheus_config(scrape_targets, scrape_interval, is_leaf=True)
        upload_config(ip, config)

    # Configure central Prometheus instance
    config = generate_prometheus_config([f"{ip}:9090" for ip in leaf_instances], scrape_interval, is_leaf=False)
    upload_config(central_instance, config)


def initialize_query_components(query_component_ips, env_vars):

    for i, ip in enumerate(query_component_ips):
        script = f"""
        export PROMETHEUS_URL=http://{env_vars["PROMETHEUS_URL"]}:9090
        export QUERY_LIST='{json.dumps(env_vars["QUERY_LIST"])}'
        export QUERY_INTERVAL={env_vars["QUERY_INTERVAL"]}
        export EXPERIMENT_DURATION={env_vars["EXPERIMENT_DURATION"]}
        export LOG_FILE=/var/log/query_component_{i}.log

        sudo apt-get update
        sudo apt-get install -y python3-pip
        pip3 install requests
        python3 /path/to/query_component.py
        """
        subprocess.run(["ssh", f"user@{ip}", script])


def collect_logs(experiment_id, component_ips, log_path):
    experiment_log_path = f"{log_path}/experiment_{experiment_id}"
    os.makedirs(experiment_log_path, exist_ok=True)

    for ip in component_ips:
        subprocess.run([
            "scp",
            f"user@{ip}:/var/log/*.log",
            f"{experiment_log_path}/"
        ])


def run_experiment(experiment, experiment_id):
    print(f"Starting experiment {experiment_id}: {experiment}")

    # Step 1: Deploy Infrastructure
    run_terraform("apply", {
        "load_generator_count": experiment["load_generators"]["count"],
        "prometheus_count": experiment["prometheus_instances"]["count"],
        "query_component_count": experiment["query_components"]["count"]
    })

    # Step 2: Retrieve IP Addresses
    load_generator_ips = get_terraform_output("load_generator_ips")
    prometheus_ips = get_terraform_output("prometheus_ips")
    query_component_ips = get_terraform_output("query_component_ips")

    # Step 3: Initialize Components
    initialize_load_generators(load_generator_ips, experiment["load_generators"]["env"])
    initialize_prometheus(prometheus_ips, load_generator_ips, experiment["prometheus_instances"]["env"]["SCRAPE_INTERVAL"])
    initialize_query_components(query_component_ips, experiment["query_components"]["env"])

    # Step 4: Run Experiment
    duration = experiment["query_components"]["env"]["EXPERIMENT_DURATION"]
    print(f"Experiment running for {duration} seconds...")
    time.sleep(duration)

    # Step 5: Collect Logs
    print("Collecting logs...")
    all_ips = load_generator_ips + prometheus_ips + query_component_ips
    collect_logs(experiment_id, all_ips, "./results")

    # Step 6: Cleanup
    print("Cleaning up resources...")
    run_terraform("destroy")


if __name__ == "__main__":
    with open("configs/experiments.json") as f:
        experiments = json.load(f)["experiments"]

    for experiment_id, experiment in enumerate(experiments, start=1):
        run_experiment(experiment, experiment_id)
        print(f"Experiment {experiment_id} completed.")

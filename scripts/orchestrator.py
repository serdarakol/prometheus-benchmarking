import subprocess
import json
import time
import os
from .prometheus import generate_prometheus_config, upload_config
import requests


def run_terraform(action, variables=None):
    if variables:
        with open("terraform/terraform.tfvars", "w") as f:
            for key, value in variables.items():
                f.write(f"{key} = {json.dumps(value)}\n")
    subprocess.run(["terraform", action, "-auto-approve"], cwd="terraform")


def get_terraform_output(output_name):
    result = subprocess.run(["terraform", "output", "-json", output_name], cwd="terraform", capture_output=True, text=True)
    return json.loads(result.stdout)


def initialize_load_generators(load_generator_VMs, envs, zone, project_id):

    for i, vm_name in enumerate(load_generator_VMs):
        env_vars = envs[i]
        command = (
            f"git clone https://github.com/serdarakol/load_generator.git &&"
            f"cd load_generator && "
            f"export LOG_FILE=load_generator_{i}.log && "
            f"export START_PORT={env_vars['START_PORT']} && "
            f"export NUM_TARGETS={env_vars['NUM_TARGETS']} && "
            f"export SEED={env_vars['SEED']} && "
            f"python3 load_generator.py &"
        )
        subprocess.run(
            [
                "gcloud", "compute", "ssh", vm_name,
                "--zone", zone,
                "--project", project_id,
                "--command", command
            ]
        )
        print(f"Initialized load generator {i} on {vm_name}")


def initialize_query_components(query_component_VMs, prometheus_url, envs, experiment_id, EXPERIMENT_DURATION, zone, project_id):
    for i, vm_name in enumerate(query_component_VMs):
        env_vars = envs[i]
        command = (
            f"git clone https://github.com/serdarakol/query_component.git &&"
            f"cd query_component && "
            f"export PROMETHEUS_URL={prometheus_url} && "
            f"export QUERY_LIST={env_vars['QUERY_LIST']} && "
            f"export EXPERIMENT_ID={experiment_id} && "
            f"export LOG_FILE=query_component_{i}.json && "
            f"export QUERY_INTERVAL={env_vars['QUERY_INTERVAL']} && "
            f"export EXPERIMENT_DURATION={EXPERIMENT_DURATION} && "
            f"export SEED={env_vars['SEED']} && "
            f"export GCS_BUCKET_NAME='prometheus-benchmarking-app-logs' && "
            f"python3 query_component.py &"
        )
        subprocess.run(
            [
                "gcloud", "compute", "ssh", vm_name,
                "--zone", zone,
                "--project", project_id,
                "--command", command
            ]
        )

        print(f"Initialized query component {i} on {vm_name}")


def initialize_prometheus(prometheus_VMs, load_generator_server_ips, load_generator_envs, scrape_interval, zone, project_id):
    ## distribute load generators among prometheus instances and flatten the list
    def flatten_scrape_targets(load_generator_server_ips, step, offset):
        return [url for i, sublist in enumerate(load_generator_server_ips[offset::step]) for url in sublist]

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
        central_config = generate_prometheus_config(all_targets, scrape_interval, is_leaf=False)
        upload_config(central_instance, zone, project_id, central_config)
        return

    # Distribute load generator servers among leaf instances and give flattened targets
    for i, leaf_ip in enumerate(leaf_instances):
        leaf_targets = flatten_scrape_targets(new_scrape_targets, len(leaf_instances), i)
        leaf_config = generate_prometheus_config(leaf_targets, scrape_interval, is_leaf=True)
        upload_config(leaf_ip, zone, project_id, leaf_config)

    # Central instance scrapes all leaf instances
    leaf_urls = [f"{ip}:9090" for ip in leaf_instances]
    central_config = generate_prometheus_config(leaf_urls, scrape_interval, is_leaf=False)
    upload_config(central_instance, zone, project_id, central_config)


def upload_logs_to_gcs(experiment_id):
    subprocess.run(
        [
            "gsutil", "-m", "cp", "-r", "logs/experiment_{experiment_id}",
            f"gs://prometheus-benchmarking-app-logs/experiment_{experiment_id}"
        ]
    )


def run_experiment(experiment, experiment_id):
    print(f"Starting experiment {experiment_id}: {experiment}")

    project_id = experiment["PROJECT"]
    region = experiment["REGION"]
    zone = experiment["ZONE"]
    EXPERIMENT_DURATION = experiment["EXPERIMENT_DURATION"]

    load_generator_count = experiment["load_generators"]["count"]
    prometheus_count = experiment["prometheus_instances"]["count"]
    query_component_count = experiment["query_components"]["count"]

    load_generator_VMs = ["load-generator-{i}" for i in range(load_generator_count)]
    prometheus_VMs = ["prometheus-{i}" for i in range(prometheus_count)]
    query_component_VMs = ["query-component-{i}" for i in range(query_component_count)]


    # Step 1: Deploying all infrastructure
    run_terraform("apply", {
        "project_id": project_id,
        "region": region,
        "zone": zone,
        "load_generator_count": load_generator_count,
        "prometheus_count": prometheus_count,
        "query_component_count": query_component_count
    })

    # Step 2: Retrieve IP Addresses
    load_generator_ips = get_terraform_output("load_generator_ips")
    prometheus_ips = get_terraform_output("prometheus_ips")


    # Step 3: Initialize Components
    load_generator_envs = experiment["load_generators"]["envs"]
    initialize_load_generators(load_generator_VMs, load_generator_envs, zone, project_id)

    scrape_interval = experiment["prometheus_instances"]["env"]["SCRAPE_INTERVAL"]

    initialize_prometheus(prometheus_VMs, load_generator_ips, load_generator_envs, scrape_interval, zone, project_id)

    central_prometheus_url = prometheus_ips[0]
    query_component_envs = experiment["query_components"]["envs"]
    initialize_query_components(query_component_VMs, central_prometheus_url, query_component_envs, experiment_id, EXPERIMENT_DURATION, zone, project_id)

    # Step 4: Run Experiment
    print(f"Experiment running for {EXPERIMENT_DURATION} seconds...")
    time.sleep(EXPERIMENT_DURATION)

    # Step 5: Retrieve Load Generator Logs
    for i, vm_name in enumerate(load_generator_VMs):
        subprocess.run(
            [
                "gcloud", "compute", "scp",
                f"{vm_name}:load_generator_{i}.log",
                f"logs/experiment_{experiment_id}/load_generator_logs/load_generator_{i}.log",
                "--zone", zone,
                "--project", project_id
            ]
        )

    # Step 6: Retrieve Prometheus metrics
    for i, prometheus_ip in enumerate(prometheus_ips):
        response = requests.get(f"http://{prometheus_ip}:9090/metrics")
        with open(f"logs/experiment_{experiment_id}/prometheus_responses/prometheus_{i}.txt", "w") as f:
            f.write(response.text)

    upload_logs_to_gcs(experiment_id)

    # Step 5: Cleanup
    print("Cleaning up resources...")
    run_terraform("destroy")


if __name__ == "__main__":
    print("Orchestrator started.")
    print("current working directory: ", os.getcwd())
    with open("configs/experiments.json") as f:
        experiments = json.load(f)["experiments"]

    for experiment_id, experiment in enumerate(experiments, start=1):
        run_experiment(experiment, experiment_id)
        print(f"Experiment {experiment_id} completed.")

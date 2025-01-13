import subprocess
import json
import os
from client_scripts import initialize_load_generators, initialize_query_components
from helpers import create_folders_and_return_path, get_experiment_id, save_log_files_to_local, upload_logs_to_gcs
from prometheus_scripts import initialize_prometheus


def run_terraform(action, variables=None):
    if variables:
        with open("terraform/terraform.tfvars", "w") as f:
            for key, value in variables.items():
                f.write(f"{key} = {json.dumps(value)}\n")
    subprocess.run(["terraform", action, "-auto-approve"], cwd="terraform")


def get_terraform_output(output_name):
    result = subprocess.run(["terraform", "output", "-json", output_name], cwd="terraform", capture_output=True, text=True)
    return json.loads(result.stdout)


def run_experiment(experiment, experiment_id):
    print(f"Starting experiment {experiment_id}: {experiment}")
    log_path, epoch_time = create_folders_and_return_path(experiment_id)

    project_id = experiment["PROJECT"]
    region = experiment["REGION"]
    zone = experiment["ZONE"]
    EXPERIMENT_DURATION = experiment["EXPERIMENT_DURATION"]

    load_generator_count = experiment["load_generators"]["count"]
    prometheus_count = experiment["prometheus_instances"]["count"]
    query_component_count = experiment["query_components"]["count"]

    load_generator_VMs = [f"load-generator-{i}" for i in range(load_generator_count)]
    prometheus_VMs = [f"prometheus-{i}" for i in range(prometheus_count)]
    query_component_VMs = [f"query-component-{i}" for i in range(query_component_count)]


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
    query_component_ips = get_terraform_output("query_component_ips")

    # Step 3: Initialize Components
    load_generator_envs = experiment["load_generators"]["envs"]
    initialize_load_generators(load_generator_VMs, load_generator_envs, zone, project_id)

    scrape_interval = experiment["prometheus_instances"]["env"]["SCRAPE_INTERVAL"]

    initialize_prometheus(prometheus_VMs, load_generator_ips, load_generator_envs, scrape_interval, zone, project_id, log_path)

    central_prometheus_url = f"http://{prometheus_ips[0]}:9090/api/v1/query"
    query_component_envs = experiment["query_components"]["envs"]
    initialize_query_components(query_component_VMs, central_prometheus_url, query_component_envs, EXPERIMENT_DURATION, zone, project_id)

    # Retrieve log files save to local and upload to GCS
    save_log_files_to_local(load_generator_ips, prometheus_ips, query_component_ips, experiment, log_path, zone, project_id)

    upload_logs_to_gcs(log_path, experiment_id, epoch_time)

    # Step 5: Cleanup
    print("Cleaning up resources...")
    run_terraform("destroy")
    print(f"Experiment {experiment_id}:{epoch_time} completed.")


if __name__ == "__main__":
    print("Orchestrator started.")
    print("current working directory: ", os.getcwd())
    with open("configs/experiments.json") as f:
        experiments = json.load(f)["experiments"]

    for i, experiment in enumerate(experiments, start=1):
        experiment_id = get_experiment_id(experiment)
        run_experiment(experiment, experiment_id)

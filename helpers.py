import subprocess
import time
import os
import json
import requests

def upload_logs_to_gcs(path, experiment_id, epoch_time):
    subprocess.run(
        [
            "gsutil", "-m", "cp", "-r", f"{path}",
            f"gs://prometheus-benchmarking-app-logs/{experiment_id}/{epoch_time}"
        ]
    )


def wait_for_startup(vm_name, zone, project_id):
    while True:
        result = subprocess.run(
            [
                "gcloud", "compute", "ssh", vm_name,
                "--zone", zone,
                "--project", project_id,
                "--command", "test -f /tmp/startup_ready && echo READY || echo STARTUP_SCRIPT_RUNNING"
            ],
            capture_output=True, text=True
        )
        if "READY" in result.stdout:
            print(f"{vm_name} is ready.")
            break
        print(f"Waiting for {vm_name}'s startup script to complete...")
        time.sleep(10)  # Check again in 10 seconds


def get_experiment_id(experiment):
    return f"experiment_{experiment['ZONE']}_p{experiment['prometheus_instances']['count']}_lg{experiment['load_generators']['count']}_qc{experiment['query_components']['count']}"


def create_folders_and_return_path(experiment_id):
    epoch_time = int(time.time())
    log_path = f"logs/{experiment_id}/{epoch_time}"
    os.makedirs(log_path, exist_ok=True)
    os.makedirs(f"{log_path}/load_generator_logs", exist_ok=True)
    os.makedirs(f"{log_path}/prometheus_responses", exist_ok=True)
    os.makedirs(f"{log_path}/query_component_logs", exist_ok=True)
    os.makedirs(f"{log_path}/prometheus_configs", exist_ok=True)
    return log_path, epoch_time


def save_log_files_to_local(load_generator_ips, prometheus_ips, query_component_ips, experiment, log_path, zone, project_id):
    load_generator_VMs = [f"load-generator-{i}" for i in range(len(load_generator_ips))]
    query_component_VMs = [f"query-component-{i}" for i in range(len(query_component_ips))]

    # Retrieve Load Generator Logs
    for i, vm_name in enumerate(load_generator_VMs):
        subprocess.run(
            [
                "gcloud", "compute", "scp",
                f"{vm_name}:load_generator/load_generator_{i}.log",
                f"{log_path}/load_generator_logs/load_generator_{i}.log",
                "--zone", zone,
                "--project", project_id
            ]
        )

    print("Retrieved Load Generator Logs")

    # Retrieve Prometheus metrics
    for i, prometheus_ip in enumerate(prometheus_ips):
        response = requests.get(f"http://{prometheus_ip}:9090/metrics")
        with open(f"{log_path}/prometheus_responses/prometheus_{i}.txt", "w") as f:
            f.write(response.text)

    print("Retrieved Prometheus Metrics")

    # Retrieve Query Component Logs
    for i, vm_name in enumerate(query_component_VMs):
        subprocess.run(
            [
                "gcloud", "compute", "scp",
                f"{vm_name}:query_component/query_component_{i}.json",
                f"{log_path}/query_component_logs/query_component_{i}.json",
                "--zone", zone,
                "--project", project_id
            ]
        )

    print("Retrieved Query Component Logs")

    experiment["log_path"] = log_path
    experiment["load_generator_ips"] = load_generator_ips
    experiment["prometheus_ips"] = prometheus_ips
    experiment["central_prometheus_url"] = prometheus_ips[0]
    experiment["query_component_ips"] = query_component_ips
    # Step 8: Save the experiment configuration
    with open(f"{log_path}/experiment.json", "w") as f:
        json.dump(experiment, f, indent=4)
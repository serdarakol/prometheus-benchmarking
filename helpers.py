import subprocess
import time
import os
import json
import requests
from google.cloud import monitoring_v3, compute_v1
import time

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

        # Capture stdout and stderr for debugging
        output = result.stdout.strip()
        error_output = result.stderr.strip()

        print(f"[DEBUG] Output from {vm_name}: '{output}'")
        if error_output:
            print(f"[ERROR] {vm_name} stderr: '{error_output}'")

        if "READY" in output:
            print(f"{vm_name} is ready.")
            break

        print(f"Waiting for {vm_name}'s startup script to complete... result: {output or 'NO OUTPUT'}")
        time.sleep(10)


def prepare_gcloud_ssh():
    subprocess.run(
        [
            "gcloud", "compute", "config-ssh"
        ]
    )


def get_experiment_id(experiment):
    return f"experiment_p{experiment['prometheus_instances']['count']}_m{experiment['prometheus_instances']['machine_type']}_lg{experiment['load_generators']['count']}x{experiment['load_generators']['envs'][0]['NUM_TARGETS']}_qc{experiment['query_components']['count']}x{experiment['query_components']['envs'][0]['NUM_THREADS']}"


def create_folders_and_return_path(experiment_id):
    epoch_time = int(time.time())
    log_path = f"logs/{experiment_id}/{epoch_time}"
    os.makedirs(log_path, exist_ok=True)
    os.makedirs(f"{log_path}/load_generator_logs", exist_ok=True)
    os.makedirs(f"{log_path}/prometheus_responses", exist_ok=True)
    os.makedirs(f"{log_path}/query_component_logs", exist_ok=True)
    os.makedirs(f"{log_path}/prometheus_configs", exist_ok=True)
    os.makedirs(f"{log_path}/analysis_result", exist_ok=True)
    os.makedirs(f"{log_path}/cpu_usages", exist_ok=True)

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
                "--project", project_id,
            ]
        )

    print("Retrieved Load Generator Logs")

    try:
        # Retrieve Prometheus metrics
        for i, prometheus_ip in enumerate(prometheus_ips):
            response = requests.get(f"http://{prometheus_ip}:9090/metrics")
            with open(f"{log_path}/prometheus_responses/prometheus_{i}.txt", "w") as f:
                f.write(response.text)

        print("Retrieved Prometheus Metrics")
    except Exception as e:
        print(f"Failed to retrieve Prometheus metrics: {e}")
        with open(f"{log_path}/prometheus_responses/prometheus_error.txt", "w") as f:
            f.write(str(e))

    # Retrieve Query Component Logs
    for i, vm_name in enumerate(query_component_VMs):
        subprocess.run(
            [
                "gcloud", "compute", "scp",
                f"{vm_name}:query_component/query_component_{i}.json",
                f"{log_path}/query_component_logs/query_component_{i}.json",
                "--zone", zone,
                "--project", project_id,
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


def get_instance_id(project_id, zone, vm_name):
    """Retrieves the instance ID for a given VM name."""
    client = compute_v1.InstancesClient()
    instance = client.get(project=project_id, zone=zone, instance=vm_name)
    return instance.id  # Returns the numeric instance ID


def get_cpu_usage_for_single_vm(project_id, zone, vm_name, experiment_duration, log_path):
    instance_id = get_instance_id(project_id, zone, vm_name)
    client = monitoring_v3.MetricServiceClient()

    now = time.time()
    start_time = now - (experiment_duration + 180)

    project_name = f"projects/{project_id}"
    filter_str = f'metric.type="compute.googleapis.com/instance/cpu/utilization" AND resource.labels.instance_id="{instance_id}"'

    interval = monitoring_v3.TimeInterval(
        start_time={"seconds": int(start_time)},
        end_time={"seconds": int(now)}
    )


    request = {
        "name": project_name,
        "filter": filter_str,
        "interval": interval,
        "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
    }

    results = client.list_time_series(request)

    cpu_data = []
    for result in results:
        for point in result.points:
            cpu_data.append({"timestamp": point.interval.start_time.timestamp(), "value": point.value.double_value})

    avg_cpu_usage = sum([data["value"] for data in cpu_data]) / len(cpu_data)
    result_json = {
        "avg_cpu_usage": avg_cpu_usage,
        "cpu_data": cpu_data,
    }
    with open(f"{log_path}/cpu_usages/{vm_name}.json", "w") as f:
        json.dump(result_json, f, indent=4)

def get_cpu_usage_for_all_vms(project_id, zone, vm_names, experiment_duration, log_path):
    for vm_name in vm_names:
        get_cpu_usage_for_single_vm(project_id, zone, vm_name, experiment_duration, log_path)

def test1():
    print("test1")
    with open("configs/experiments.json") as f:
        experiments = json.load(f)["experiments"]
    experiment = experiments[0]
    save_log_files_to_local([
  "34.59.229.53",
  "34.30.169.157",
],
 [
  "34.58.111.105",
],
[
  "34.57.119.214",
  "34.123.108.69",
], experiment, "logs/experiment_p1_me2-small_lg2x500_qc2x400/1738707106", "us-central1-a", "prometheus-benchmarking-app")
    upload_logs_to_gcs("logs/experiment_p1_me2-small_lg2x500_qc2x400/1738707106", "experiment_p1_me2-small_lg2x500_qc2x400", 1738707106)

if __name__ == "__main__":
    #get_cpu_usage_for_all_vms("prometheus-benchmarking-app", "us-central1-a", ["load-generator-0", "load-generator-1"], 600, "logs/experiment_p1_me2-micro_lg2x50_qc2x100/1738524193")
    test1()
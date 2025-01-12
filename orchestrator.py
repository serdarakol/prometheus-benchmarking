import subprocess
import json
import time
import os
from prometheus_helper import generate_prometheus_config, upload_config
import requests
from concurrent.futures import ThreadPoolExecutor


def run_terraform(action, variables=None):
    if variables:
        with open("terraform/terraform.tfvars", "w") as f:
            for key, value in variables.items():
                f.write(f"{key} = {json.dumps(value)}\n")
    subprocess.run(["terraform", action, "-auto-approve"], cwd="terraform")


def get_terraform_output(output_name):
    result = subprocess.run(["terraform", "output", "-json", output_name], cwd="terraform", capture_output=True, text=True)
    return json.loads(result.stdout)


def initialize_single_load_generator(vm_name, env_vars, zone, project_id, i):
    wait_for_startup(vm_name, zone, project_id)
    command = (
        f"while sudo fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do echo 'Waiting for APT lock...'; sleep 5; done && "
        f"sudo apt-get install -y git && "
        f"git clone https://github.com/serdarakol/load_generator.git && "
        f"cd load_generator && "
        f"export LOG_FILE=load_generator_{i}.log && "
        f"export START_PORT={env_vars['START_PORT']} && "
        f"export NUM_TARGETS={env_vars['NUM_TARGETS']} && "
        f"export SEED={env_vars['SEED']} && "
        f"pip3 install prometheus_client && "
        f"nohup python3 load_generator.py > load_generator.log 2>&1 & disown"
    )
    print(f"Executing command on {vm_name}: {command}")
    subprocess.Popen(
        [
            "gcloud", "compute", "ssh", vm_name,
            "--zone", zone,
            "--project", project_id,
            "--command", command
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"Initialized load generator {i} on {vm_name}")


def initialize_load_generators(load_generator_VMs, envs, zone, project_id):
    with ThreadPoolExecutor() as executor:
        for i, vm_name in enumerate(load_generator_VMs):
            executor.submit(initialize_single_load_generator, vm_name, envs[i], zone, project_id, i)


def initialize_single_query_component(vm_name, prometheus_url, env_vars, EXPERIMENT_DURATION, zone, project_id, i):
    wait_for_startup(vm_name, zone, project_id)

    query_list_json = json.dumps(env_vars["QUERY_LIST"]).replace('"', '\\"')
    command = (
        f"while sudo fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do echo 'Waiting for APT lock...'; sleep 5; done && "
        f"sudo apt-get install -y git && "
        f"git clone https://github.com/serdarakol/query_component.git && "
        f"cd query_component && "
        f"echo Running export commands... && "
        f"export PROMETHEUS_URL={prometheus_url} && "
        f"export QUERY_LIST=\"{query_list_json}\" && "
        f"export LOG_FILE=query_component_{i}.json && "
        f"export QUERY_INTERVAL={env_vars['QUERY_INTERVAL']} && "
        f"export EXPERIMENT_DURATION={EXPERIMENT_DURATION} && "
        f"export SEED={env_vars['SEED']} && "
        f"pip3 install requests && "
        f"python3 query_component.py &"
    )
    print(f"Executing query component on {vm_name} VM")
    print(f"Command: {command}")
    subprocess.run(
        [
            "gcloud", "compute", "ssh", vm_name,
            "--zone", zone,
            "--project", project_id,
            "--command", command
        ]
    )


def initialize_query_components(query_component_VMs, prometheus_url, envs, EXPERIMENT_DURATION, zone, project_id):
    with ThreadPoolExecutor() as executor:
        for i, vm_name in enumerate(query_component_VMs):
            executor.submit(initialize_single_query_component, vm_name, prometheus_url, envs[i], EXPERIMENT_DURATION, zone, project_id, i)


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


def upload_logs_to_gcs(path):
    subprocess.run(
        [
            "gsutil", "-m", "cp", "-r", f"{path}",
            f"gs://prometheus-benchmarking-app-logs"
        ]
    )


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


def run_experiment(experiment, experiment_id):
    print(f"Starting experiment {experiment_id}: {experiment}")

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

    print("Waiting for 1 minute before starting the experiment... to wait all the vms get ready")
    time.sleep(60)  # Wait for 1 minute before starting the experiment

    # Step 3: Initialize Components
    load_generator_envs = experiment["load_generators"]["envs"]
    initialize_load_generators(load_generator_VMs, load_generator_envs, zone, project_id)

    scrape_interval = experiment["prometheus_instances"]["env"]["SCRAPE_INTERVAL"]

    initialize_prometheus(prometheus_VMs, load_generator_ips, load_generator_envs, scrape_interval, zone, project_id)

    central_prometheus_url = f"http://{prometheus_ips[0]}:9090/api/v1/query"
    query_component_envs = experiment["query_components"]["envs"]
    initialize_query_components(query_component_VMs, central_prometheus_url, query_component_envs, EXPERIMENT_DURATION, zone, project_id)

    epoch_time = int(time.time())
    log_path = f"logs/{experiment_id}/{epoch_time}"
    os.makedirs(log_path, exist_ok=True)
    os.makedirs(f"{log_path}/load_generator_logs", exist_ok=True)
    os.makedirs(f"{log_path}/prometheus_responses", exist_ok=True)
    os.makedirs(f"{log_path}/query_component_logs", exist_ok=True)

    # Step 5: Retrieve Load Generator Logs
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

    # Step 6: Retrieve Prometheus metrics
    for i, prometheus_ip in enumerate(prometheus_ips):
        response = requests.get(f"http://{prometheus_ip}:9090/metrics")
        with open(f"{log_path}/prometheus_responses/prometheus_{i}.txt", "w") as f:
            f.write(response.text)

    # Step 7: Retrieve Query Component Logs
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

    # Step 8: Save the experiment configuration
    with open(f"{log_path}/experiment.json", "w") as f:
        json.dump(experiment, f, indent=4)

    upload_logs_to_gcs(log_path)

    # Step 5: Cleanup
    print("Cleaning up resources...")
    run_terraform("destroy")


def get_experiment_id(experiment):
    return f"experiment_{experiment['ZONE']}_p{experiment['prometheus_instances']['count']}_lg{experiment['load_generators']['count']}_qc{experiment['query_components']['count']}"

if __name__ == "__main__":
    print("Orchestrator started.")
    print("current working directory: ", os.getcwd())
    with open("configs/experiments.json") as f:
        experiments = json.load(f)["experiments"]

    for i, experiment in enumerate(experiments, start=1):
        experiment_id = get_experiment_id(experiment)
        run_experiment(experiment, experiment_id)
        print(f"Experiment {experiment_id} completed.")

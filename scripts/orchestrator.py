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

def upload_script(ip, local_path, remote_path):
    subprocess.run(["scp", local_path, f"user@{ip}:{remote_path}"])


def initialize_load_generators(load_generator_ips, envs):

    for i, ip in enumerate(load_generator_ips):
        env_vars = envs[i]
        script = f"""
        export START_PORT={env_vars["START_PORT"]}
        export NUM_TARGETS={env_vars["NUM_TARGETS"]}
        export SEED={env_vars["SEED"]}
        export LOG_FILE=/var/log/load_generator_{i}.log

        python3 /path/to/load_generator.py &
        """
        subprocess.run(["ssh", f"user@{ip}", script])


def initialize_prometheus(prometheus_ips, load_generator_server_ips, load_generator_envs, scrape_interval):
    ## distribute load generators among prometheus instances and flatten the list
    def flatten_scrape_targets(load_generator_server_ips, step, offset):
        return [url for i, sublist in enumerate(load_generator_server_ips[offset::step]) for url in sublist]

    central_instance = prometheus_ips[0]
    leaf_instances = prometheus_ips[1:]

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
        upload_config(central_instance, central_config)
        return

    # Distribute load generator servers among leaf instances and give flattened targets
    for i, leaf_ip in enumerate(leaf_instances):
        leaf_targets = flatten_scrape_targets(new_scrape_targets, len(leaf_instances), i)
        leaf_config = generate_prometheus_config(leaf_targets, scrape_interval, is_leaf=True)
        upload_config(leaf_ip, leaf_config)

    # Central instance scrapes all leaf instances
    leaf_urls = [f"{ip}:9090" for ip in leaf_instances]
    central_config = generate_prometheus_config(leaf_urls, scrape_interval, is_leaf=False)
    upload_config(central_instance, central_config)


def initialize_query_components(query_component_ips, prometheus_url, envs):

    for i, ip in enumerate(query_component_ips):
        env_vars = envs[i]
        script = f"""
        export PROMETHEUS_URL=http://{prometheus_url}:9090
        export QUERY_LIST='{json.dumps(env_vars["QUERY_LIST"])}'
        export QUERY_INTERVAL={env_vars["QUERY_INTERVAL"]}
        export EXPERIMENT_DURATION={env_vars["EXPERIMENT_DURATION"]}
        export LOG_FILE=/var/log/query_component_{i}.log

        python3 /path/to/query_component.py &
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

    for i, ip in enumerate(load_generator_ips):
        upload_script(ip, "./scripts/load_generator.py", "/path/to/load_generator.py")

    for i, ip in enumerate(query_component_ips):
        upload_script(ip, "./scripts/query_component.py", "/path/to/query_component.py")


    # Step 3: Initialize Components
    load_generator_envs = experiment["load_generators"]["envs"]
    initialize_load_generators(load_generator_ips, load_generator_envs)

    scrape_interval = experiment["prometheus_instances"]["env"]["SCRAPE_INTERVAL"]

    initialize_prometheus(prometheus_ips, load_generator_ips, load_generator_envs, scrape_interval)

    central_prometheus_url = prometheus_ips[0]
    query_component_envs = experiment["query_components"]["envs"]
    initialize_query_components(query_component_ips, central_prometheus_url,  query_component_envs)

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
    print("Orchestrator started.")
    print("current working directory: ", os.getcwd())
    with open("configs/experiments.json") as f:
        experiments = json.load(f)["experiments"]

    for experiment_id, experiment in enumerate(experiments, start=1):
        run_experiment(experiment, experiment_id)
        print(f"Experiment {experiment_id} completed.")

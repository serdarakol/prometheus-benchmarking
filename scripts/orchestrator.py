import subprocess
import json
import time

def run_experiment(config):
    print(f"Running experiment: {config}")
    # Update Terraform variables
    with open("terraform.tfvars", "w") as f:
        f.write(f"load_generator_count = {config['load_generators']}\n")
        f.write(f"query_component_count = {config['query_components']}\n")

    # Apply Terraform configuration
    subprocess.run(["terraform", "apply", "-auto-approve"])

    # Wait for experiment duration
    print("Running experiment...")
    time.sleep(600)  # Example: 10 minutes

    # Collect logs
    subprocess.run(["scp", "user@prometheus:/path/to/logs", "./results/"])

    # Destroy infrastructure
    subprocess.run(["terraform", "destroy", "-auto-approve"])

if __name__ == "__main__":
    with open("experiments.json", "r") as f:
        experiments = json.load(f)["experiments"]

    for experiment in experiments:
        run_experiment(experiment)

from concurrent.futures import ThreadPoolExecutor, wait
import subprocess
import json
import time

from helpers import wait_for_startup


def initialize_single_load_generator(vm_name, env_vars, zone, project_id, i):
    wait_for_startup(vm_name, zone, project_id)
    command = (
        f"git clone https://github.com/serdarakol/load_generator.git && "
        f"cd load_generator && "
        f"export LOG_FILE=load_generator_{i}.log && "
        f"export START_PORT={env_vars['START_PORT']} && "
        f"export NUM_TARGETS={env_vars['NUM_TARGETS']} && "
        f"export SEED={env_vars['SEED']} && "
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


def stop_single_load_generator(vm_name, zone, project_id):
    print(f"Stopping load generator on {vm_name}")
    subprocess.run(
        [
            "gcloud", "compute", "ssh", vm_name,
            "--zone", zone,
            "--project", project_id,
            "--command", "pkill -f load_generator.py"
        ]
    )
    print(f"Stopped load generator on {vm_name}")


def stop_load_generators(load_generator_VMs, zone, project_id):
    with ThreadPoolExecutor() as executor:
        for vm_name in load_generator_VMs:
            executor.submit(stop_single_load_generator, vm_name, zone, project_id)


def initialize_single_query_component(vm_name, prometheus_url, env_vars, EXPERIMENT_DURATION, zone, project_id, i):
    wait_for_startup(vm_name, zone, project_id)

    query_list_json = json.dumps(env_vars["QUERY_LIST"]).replace('"', '\\"')
    command = (
        f"git clone https://github.com/serdarakol/query_component.git && "
        f"cd query_component && "
        f"echo Running export commands... && "
        f"export PROMETHEUS_URL={prometheus_url} && "
        f"export QUERY_LIST=\"{query_list_json}\" && "
        f"export LOG_FILE=query_component_{i}.json && "
        f"export QUERY_INTERVAL={env_vars['QUERY_INTERVAL']} && "
        f"export NUM_THREADS={env_vars['NUM_THREADS']} && "
        f"export EXPERIMENT_DURATION={EXPERIMENT_DURATION} && "
        f"export SEED={env_vars['SEED']} && "
        f"python3 query_component.py "
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
    print(f"query component executed on {vm_name}")


def initialize_query_components(query_component_VMs, prometheus_url, envs, EXPERIMENT_DURATION, zone, project_id):
    with ThreadPoolExecutor() as executor:
        future_to_vm = {
            executor.submit(initialize_single_query_component, vm_name, prometheus_url, envs[i], EXPERIMENT_DURATION, zone, project_id, i): vm_name
            for i, vm_name in enumerate(query_component_VMs)
        }

        done, not_done = wait(future_to_vm.keys(), timeout=(EXPERIMENT_DURATION + 60))

        for future in done:
            vm_name = future_to_vm[future]
            try:
                future.result()
                print(f"initialized query component on {vm_name}")
            except Exception as e:
                print(f"Error initializing {vm_name}: {e}")

        if not_done:
            print(f"timeout reached! {len(not_done)} query components did not complete in time.")
            for future in not_done:
                vm_name = future_to_vm[future]
                print(f"{vm_name} executed but not finised, possiible hanging queries still")
                future.cancel()

    print("Initialization completed (or timed out). Moving on...")

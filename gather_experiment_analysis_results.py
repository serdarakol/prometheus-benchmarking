import os
import json
import pandas as pd

def parse_experiment_id(exp_id):
    details = {
        "experiment_id": exp_id,
        "prometheus_count": None,
        "machine_type": None,
        "load_generators_count": None,
        "num_targets": None,
        "query_components_count": None,
        "num_threads": None
    }
    try:
        # Split by underscore; expected parts:
        # [ "experiment", "p{...}", "m{...}", "lg{...}x{...}", "qc{...}x{...}" ]
        parts = exp_id.split("_")
        if len(parts) >= 5:
            details["prometheus_count"] = parts[1].lstrip("p")
            details["machine_type"] = parts[2].lstrip("m")
            lg_part = parts[3].lstrip("lg")
            qc_part = parts[4].lstrip("qc")
            if "x" in lg_part:
                lg_count, num_targets = lg_part.split("x")
                details["load_generators_count"] = lg_count
                details["num_targets"] = num_targets
            if "x" in qc_part:
                qc_count, num_threads = qc_part.split("x")
                details["query_components_count"] = qc_count
                details["num_threads"] = num_threads
    except Exception as e:
        print(f"Error parsing experiment id '{exp_id}': {e}")
    return details

def generate_excel_from_logs(base_logs_dir="logs", output_file="experiment_results.xlsx"):
    rows = []

    if not os.path.exists(base_logs_dir):
        print(f"Directory '{base_logs_dir}' does not exist.")
        return

    # Iterate over experiments
    for exp_id in os.listdir(base_logs_dir):
        exp_dir = os.path.join(base_logs_dir, exp_id)
        if not os.path.isdir(exp_dir):
            continue

        # parsing the experiment id for setup details
        exp_details = parse_experiment_id(exp_id)

        # iterating over timestamp folder === > different executions
        for timestamp in os.listdir(exp_dir):
            execution_dir = os.path.join(exp_dir, timestamp)
            if not os.path.isdir(execution_dir):
                continue

            #analysis_result folder inside the timestamp folder
            analysis_dir = os.path.join(execution_dir, "analysis_result")
            if not os.path.exists(analysis_dir):
                continue

            file_path = os.path.join(analysis_dir, "query_stats.json")
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"Error reading JSON file '{file_path}': {e}")
                continue
            overall = data.get("overall")
            if overall is None:
                print(f"No 'overall' data in '{file_path}'. Skipping.")
                continue
            #row with overall metrics and experiment run details
            row = {
                "experiment_id": exp_id,
                "timestamp": timestamp,
                "number_of_successfull_requests": overall.get("count"),
                "mean": overall.get("mean"),
                "std": overall.get("std"),
                "min": overall.get("min"),
                "median": overall.get("median"),
                "max": overall.get("max"),
                "quantile_99": overall.get("quantile_99"),
                "quantile_95": overall.get("quantile_95"),
                "quantile_75": overall.get("quantile_75"),
                "overall_success_rate": overall.get("success_rate")
            }

            row.update(exp_details)
            rows.append(row)

    if rows:
        df = pd.DataFrame(rows)

        df.to_excel(output_file, index=False)
        print(f"Excel file generated and saved as '{output_file}'.")
    else:
        print("No experiment data found.")


if __name__ == "__main__":
    generate_excel_from_logs()

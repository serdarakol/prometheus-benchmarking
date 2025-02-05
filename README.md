# prometheus-benchmarking
cloud service benchmarking - benchmarking prometheus query latency under scale-out


benchmarking-prometheus-latency/
├── configs/                # Configurations for Prometheus and experiments
│   ├── prometheus.yml.tpl  # Template for Prometheus configuration
│   └── experiments.json    # Experiment configurations (e.g., number of targets, query interval)
├── terraform/              # Terraform deployment files
│   ├── main.tf             # Main Terraform script
│   ├── variables.tf        # Terraform variables
│   ├── outputs.tf          # Terraform outputs
│   └── startup-scripts     #startup script folder
│       ├── load_generator.sh
│       ├── prometheus.sh
│       └── query_component.sh
├── scripts/                # Python scripts for load generation, querying, and orchestration
│   ├── prometheus.py       # Generates Prometheus configuration
│   └── orchestrator.py     # Orchestrates the experiments
├── logs/                   # Logs from experiments (also uploaded to the google cloud storage)
│   ├── {experiment_id}
├── .env                    # Environment variables file
└── README.md               # Documentation for the repository


first things first
download terraform

run below

gcloud auth login to login your gcloud account

then go to terraform folder with cd terraform
terraform init
terraform plan
terraform apply

make sure your role has permissions

run
```pip3 install -r requirements.txt```

then configure the experiments.json file under configs folder
then
```python3 orchestrator.py```

after runnning all your experiments run
```python3 gather_experiment_analysis_results.py```
# prometheus-benchmarking
cloud service benchmarking - benchmarking prometheus query latency under scale-out

pip3 install prometheus_client and stuff


```brew install prometheus``` or corresponding commands for installing prometheus

prometheus --config.file=<config yml file>


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
│   ├── experiment_{experiment_id}
├── .env                    # Environment variables file
└── README.md               # Documentation for the repository


first things first
download terraform

run below

gcloud auth application-default login

then go to terraform folder
terraform init
terraform plan
terraform apply

make sure your role has permission


below error solved by adding ' application-default ' option to the gcloud auth login command
google_compute_network.vpc_network: Creating...
╷
│ Error: Error creating Network: googleapi: Error 403: Required 'compute.networks.create' permission for 'projects/prometheus-benchmarking-app/global/networks/benchmark-network', forbidden
│
│   with google_compute_network.vpc_network,
│   on main.tf line 8, in resource "google_compute_network" "vpc_network":
│    8: resource "google_compute_network" "vpc_network" {
│
╵


scp command asks for permission

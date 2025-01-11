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
│   ├── load_generator.tf   # Terraform script for load generators
│   ├── prometheus.tf       # Terraform script for Prometheus deployment
│   └── query_component.tf  # Terraform script for query components
├── scripts/                # Python scripts for load generation, querying, and orchestration
│   ├── load_generator.py   # Load generator script
│   ├── query_component.py  # Querying component script
│   ├── prometheus_config_generator.py # Generates Prometheus configuration
│   └── orchestrator.py     # Orchestrates the experiments
├── docker/                 # Dockerfiles for components (optional)
│   ├── Dockerfile.load     # Dockerfile for load generator
│   ├── Dockerfile.query    # Dockerfile for query component
│   └── Dockerfile.prometheus  # Dockerfile for Prometheus
├── logs/                   # Logs from experiments
│   ├── raw/                # Raw logs from components
│   ├── refined/            # Processed logs for analysis
│   └── analysis/           # Analysis results
├── results/                # Experiment results
│   └── experiment_01/      # Separate folder for each experiment
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

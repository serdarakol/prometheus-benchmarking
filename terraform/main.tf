provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

### NETWORK
resource "google_compute_network" "vpc_network" {
  name = "benchmark-network"
  auto_create_subnetworks = true
}

### FIREWALL
resource "google_compute_firewall" "allow_all" {
  name = "allow-all"
  network = google_compute_network.vpc_network.id

  allow {
    protocol = "tcp"
    ports = ["0-65535"]
  }

  source_ranges = ["0.0.0.0/0"]
}

### SUT INSTANCE
module "prometheus" {
  source = "./prometheus.tf"
}

### BENCHMARK CLIENT load generator component
module "load_generators" {
  source = "./load_generator.tf"
}

### BENCHMARK CLIENT query component
module "query_components" {
  source = "./query_component.tf"
}

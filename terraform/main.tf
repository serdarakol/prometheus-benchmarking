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

resource "google_compute_instance" "load_generator" {
  count         = var.load_generator_count
  name          = "load-generator-${count.index}"
  machine_type  = "e2-standard-2"
  zone          = var.zone

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }

  network_interface {
    network = google_compute_network.vpc_network.id
    access_config {
      # Include this section to give the VM an external IP address
    }
  }

  metadata_startup_script = <<EOT
    #!/bin/bash
    export DEBIAN_FRONTEND=noninteractive
    sudo apt-get update
    sudo apt-get install -y python3-pip
    pip3 install prometheus_client
    echo "Load generator ready."
  EOT
}

resource "google_compute_instance" "prometheus" {
  count         = var.prometheus_count
  name          = "prometheus-${count.index}"
  machine_type  = "e2-standard-4"
  zone          = var.zone

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }

  network_interface {
    network = google_compute_network.vpc_network.id
    access_config {
      # Include this section to give the VM an external IP address
    }
  }

  metadata_startup_script = <<EOT
    #!/bin/bash
    export DEBIAN_FRONTEND=noninteractive
    sudo apt-get update
    sudo apt-get install -y prometheus
    echo "Prometheus instance ${count.index} ready."
  EOT
}



resource "google_compute_instance" "query_component" {
  count         = var.query_component_count
  name          = "query-component-${count.index}"
  machine_type  = "e2-standard-2"
  zone          = var.zone

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }

  network_interface {
    network = google_compute_network.vpc_network.id
    access_config {
      # Include this section to give the VM an external IP address
    }
  }

  metadata_startup_script = <<EOT
    #!/bin/bash
    export DEBIAN_FRONTEND=noninteractive
    sudo apt-get update
    sudo apt-get install -y python3-pip
    pip3 install requests
    echo "Query component ready."
  EOT
}


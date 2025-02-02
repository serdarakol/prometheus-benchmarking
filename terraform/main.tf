provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
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
    network = "default"
  }

  metadata_startup_script = file("startup-scripts/load_generator.sh")
}

resource "google_compute_instance" "prometheus" {
  count         = var.prometheus_count
  name          = "prometheus-${count.index}"
  machine_type  = var.prometheus_machine_type
  zone          = var.zone

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }

  network_interface {
    network = "default"
    access_config {
      # adds external ip
    }
  }

  metadata_startup_script = file("startup-scripts/prometheus.sh")
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
    network = "default"
  }

  metadata_startup_script = file("startup-scripts/query_component.sh")
}


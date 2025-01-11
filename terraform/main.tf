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

### SERVICE ACCOUNT
resource "google_service_account" "vm_service_account" {
  account_id   = "vm-storage-admin"
  display_name = "VM Service Account for Storage Admin"
}

### SERVICE ACCOUNT IAM POLICY
resource "google_project_iam_member" "vm_storage_admin_role" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.vm_service_account.email}"
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

  service_account {
    email = google_service_account.vm_service_account.email
    scopes = ["https://www.googleapis.com/auth/devstorage.full_control"]
  }

  metadata_startup_script = file("startup-scripts/load_generator.sh")
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
    network = google_compute_network.vpc_network.id
    access_config {
      # Include this section to give the VM an external IP address
    }
  }

  service_account {
    email  = google_service_account.vm_service_account.email
    scopes = ["https://www.googleapis.com/auth/devstorage.full_control"]
  }

  metadata_startup_script = file("startup-scripts/query_component.sh")
}


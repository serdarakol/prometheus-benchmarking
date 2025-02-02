provider "google" {
  project = "prometheus-benchmarking-app"
  region  = "us-central1"
  zone    = "us-central1-a"
}

### FIREWALL
resource "google_compute_firewall" "allow_all" {
  name = "allow-all"
  network = "default"

  allow {
    protocol = "tcp"
    ports = ["0-65535"]
  }

  source_ranges = ["0.0.0.0/0"]
}

resource "google_compute_instance" "orchestrator-host" {
  name          = "orchestrator-host"
  machine_type  = "e2-standard-2"
  zone          = "us-central1-a"

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

  service_account {
    email  = google_service_account.orchestrator_sa.email
    scopes = ["cloud-platform"]
  }


  metadata_startup_script = file("orchestrator_host.sh")
}

# Create a dedicated service account for the orchestrator
resource "google_service_account" "orchestrator_sa" {
  account_id   = "orchestrator-sa"
  display_name = "Orchestrator Service Account"
}

# Grant IAM roles to the service account
resource "google_project_iam_member" "orchestrator_compute_admin" {
  project = "prometheus-benchmarking-app"
  role    = "roles/compute.admin"
  member  = "serviceAccount:${google_service_account.orchestrator_sa.email}"
}

resource "google_project_iam_member" "orchestrator_iam_ssh" {
  project = "prometheus-benchmarking-app"
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.orchestrator_sa.email}"
}

# Grant Storage Admin role to the orchestrator service account
resource "google_project_iam_member" "orchestrator_storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.orchestrator_sa.email}"
}

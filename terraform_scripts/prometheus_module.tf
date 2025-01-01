resource "google_compute_instance" "prometheus" {
  name          = "prometheus"
  machine_type  = "e2-standard-4"
  zone          = var.zone

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  metadata_startup_script = <<-EOT
    #!/bin/bash
    sudo apt-get update
    sudo apt-get install -y prometheus
    mv /path/to/generated_prometheus.yml /etc/prometheus/prometheus.yml
    systemctl restart prometheus
  EOT
}

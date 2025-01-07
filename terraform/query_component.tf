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

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
    access_config {}
  }

  metadata_startup_script = templatefile("${path.module}/load_generator_startup.sh.tpl", {
    start_port   = 8000 + count.index * 5
    num_targets  = 5
  })
}
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Include other components
module "load_generators" {
  source = "./load_generator.tf"
}

module "prometheus" {
  source = "./prometheus.tf"
}

module "query_components" {
  source = "./query_component.tf"
}

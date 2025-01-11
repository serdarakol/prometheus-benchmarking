variable "project_id" {
  description = "Google Cloud project ID"
  default     = "prometheus-benchmarking-app"
}

variable "region" {
  description = "Google Cloud region"
  default     = "us-central1"
}

variable "zone" {
  description = "Google Cloud zone"
  default     = "us-central1-a"
}

variable "load_generator_count" {
  description = "Number of load generator VMs"
  default     = 1
}

variable "prometheus_count" {
  description = "Number of Prometheus instances (including central and leaf)"
  default     = 1
}

variable "query_component_count" {
  description = "Number of query component VMs"
  default     = 1
}

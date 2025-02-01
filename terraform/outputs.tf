output "load_generator_ips" {
  value = [for instance in google_compute_instance.load_generator :
           instance.network_interface[0].network_ip]
}

output "prometheus_ips" {
  value = [for instance in google_compute_instance.prometheus :
           instance.network_interface[0].access_config[0].nat_ip]
}

output "query_component_ips" {
  value = [for instance in google_compute_instance.query_component :
           instance.network_interface[0].network_ip]
}
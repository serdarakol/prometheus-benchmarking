export DEBIAN_FRONTEND=noninteractive
sudo apt-get update
sudo apt-get install -y prometheus
echo "Prometheus instance ${count.index} ready."
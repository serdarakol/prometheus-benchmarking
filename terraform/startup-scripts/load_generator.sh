export DEBIAN_FRONTEND=noninteractive
sudo apt-get update
sudo apt-get install -y python3-pip
sudo apt-get install -y git

pip3 install prometheus_client
pip3 install google-cloud-storage

echo "Load generator ready."

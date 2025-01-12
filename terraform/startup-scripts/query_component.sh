export DEBIAN_FRONTEND=noninteractive
sudo apt-get update
sudo apt-get install -y python3-pip
sudo apt-get install -y git

pip3 install requests
pip3 install google-cloud-storage

echo "Query component ready."

touch /tmp/startup_ready

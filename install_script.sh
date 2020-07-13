#!/bin/bash
echo "Updating and Upgrading the repositories"
sudo apt-get update
sudo apt-get upgrade -y
echo "Installing docker"
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo groupadd docker
sudo gpasswd -a $USER docker
sudo service docker restart
newgrp docker
echo "Loading the docker image"
docker load --input birdv01.tar
echo "--------------------------------"
echo "Configuring PI service and PI controller"
echo "Installing flask"
sudo apt-get install python3-pip
sudo pip3 install flask
sudo pip3 install requests
sudo pip3 install docker
sudo pip3 install netifaces
sudo apt-get install nmap -y
sudo pip3 install python-nmap
echo "Installing Picamera"
sudo pip3 install "picamera[array]"
echo "Installing GPIO"
sudo pip3 install RPi.GPIO
echo "Installing PiJuice"
sudo apt-get install pijuice-gui -y
echo "--------------------------------"
echo "Initiate cron job, copy PiService and PiController"
cp PiServices.py /home/pi/
cp PiController.py /home/pi/
cp AWS_Keys.txt /home/pi/
touch run.cron
echo '@reboot cd /home/pi/ && /usr/bin/python3 /home/pi/PiServices.py &' >>run.cron
echo '@reboot sleep 10 && /usr/bin/python3 /home/pi/PiController.py &' >>run.cron
echo '@reboot sleep 10 && /usr/bin/python3 /home/pi/uploadState.py &' >>run.cron
crontab run.cron
rm run.cron












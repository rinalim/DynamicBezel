sudo apt install python-pyudev python-bitstring -y
sudo pip install keyboard

rm -rf /opt/retropie/configs/all/DynamicBezel/
mkdir /opt/retropie/configs/all/DynamicBezel/
cp -f -r ./DynamicBezel /opt/retropie/configs/all/

sudo chmod 755 /opt/retropie/configs/all/DynamicBezel/omxiv-bezel

sudo sed -i '/DynamicBezel.py/d' /opt/retropie/configs/all/runcommand-onstart.sh
echo 'sudo /usr/bin/python /opt/retropie/configs/all/DynamicBezel/DynamicBezel.py /dev/input/js0 > /dev/null 2>&1 &' >> /opt/retropie/configs/all/runcommand-onstart.sh
sudo sed -i '/DynamicBezel/d' /opt/retropie/configs/all/runcommand-onend.sh
echo 'sudo pkill -ef DynamicBezel > /dev/null 2>&1' >> /opt/retropie/configs/all/runcommand-onend.sh
sudo sed -i '/gpu_mem/d' /boot/config.txt
echo 'gpu_mem=256' >> /boot/config.txt
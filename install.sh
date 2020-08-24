sudo apt install python-pyudev -y

rm -rf /opt/retropie/configs/all/DynamicBezel/
mkdir /opt/retropie/configs/all/DynamicBezel/
cp -f -r ./DynamicBezel /opt/retropie/configs/all/

sudo chmod 755 /opt/retropie/configs/all/DynamicBezel/omxiv-bezel

sudo sed -i '/DynamicBezel.py/d' /opt/retropie/configs/all/autostart.sh
sudo sed -i '1i\\/usr/bin/python /opt/retropie/configs/all/DynamicBezel/DynamicBezel.py &' /opt/retropie/configs/all/autostart.sh

sudo sed -i '/DynamicBezel.py/d' /opt/retropie/configs/all/runcommand-onstart.sh
echo '/usr/bin/python /opt/retropie/configs/all/DynamicBezel/DynamicBezel.py &' >> /opt/retropie/configs/all/runcommand-onstart.sh
sudo sed -i '/DynamicBezel.py/d' /opt/retropie/configs/all/runcommand-onend.sh
echo 'pkill -ef DynamicBezel.py' >> /opt/retropie/configs/all/runcommand-onend.sh

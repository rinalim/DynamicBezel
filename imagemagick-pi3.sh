mkdir ~/src
cd ~/src
wget http://www.imagemagick.org/download/releases/ImageMagick-6.9.10-33.tar.xz
sudo apt-get install build-essential checkinstall -y
tar xf ImageMagick-6.9.10-33.tar.xz
d ImageMagick-6.9.10-33/
./configure
make -j2
sudo checkinstall
sudo ldconfig
convert -version

# Bottle Label

Shoots labels out a Dymo 450 via and Alexa skill.

Set up a skill and use the provided `interaction-model.json`. 

Sorry this README is sparse. If you care for more instructions,
please create an issue. Thanks.

```shell
sudo apt update
sudo apt install -y vim unattended-upgrades \
  python3 python3-pip python3-venv \
  cups cups-client printer-driver-dymo

sudo vim /etc/vim/vimrc.local
# set mouse=
# set ttymouse=

sudo vim /etc/apt/apt.conf.d/50unattended-upgrades
# Automatic-Reboot "true";
# Automatic-Reboot-Time "02:00";

# Edit static IP in /etc/dhcpcd.conf and reboot

# Download ppds for printer from
# https://www.dymo-label-printers.co.uk/news/download-dymo-sdk-for-linux.html
# Basically followed this guide:
# https://www.baitando.com/it/2017/12/12/install-dymo-labelwriter-on-headless-linux
sudo mkdir -p /usr/share/cups/model/dymo
sudo cp ./dymo-cups-drivers-1.4.0.5/ppd/lw450.ppd /usr/share/cups/model/dymo/

# List pritners
sudo lpinfo -v
# usb://DYMO/LabelWriter%20450?serial=01010112345600

sudo lpadmin -p dymo450 -v  usb://DYMO/LabelWriter%20450?serial=01010112345600 -P /usr/share/cups/model/dymo/lw450.ppd
sudo lpstat -v
sudo cupsenable dymo450
sudo cupsaccept dymo450
lp -d dymo450 <(echo hello)

# Fix the PPD to print multiple pages
sudo vim /etc/cups/ppd/dymo450.ppd
# Change
# *cupsManualCopies: False
# to
# *cupsManualCopies: True
sudo systemctl restart cups

# Create bottle service account
sudo useradd -r bottle
sudo mkdir /srv/bottle
sudo chown -R bottle:bottle /srv/bottle

# Copy this project into /srv/bottle/bottle-label
sudo chown -R bottle:bottle /srv/bottle

# Switch to bottle user & init server
sudo su - bottle
cd /srv/bottle
python3 -m venv venv
./venv/bin/python -m pip install -U pip wheel setuptools
./venv/bin/python -m pip install -e ./bottle-label

# Install the below systemd service into
# /etc/systemd/system/bottle-label.service
sudo systemctl daemon-reload
sudo systemctl enable bottle-label
sudo systemctl start bottle-label
sudo systemctl status bottle-label
```

```text
[Unit]
Description=Bottle label
After=network.target

[Service]
Type=simple
User=bottle
Group=bottle
WorkingDirectory=/srv/bottle
ExecStart=/srv/bottle/venv/bin/python3 -m label.server --baby-name 'foobar'

[Install]
WantedBy=multi-user.target
```

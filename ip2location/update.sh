#!/bin/bash

cd $(dirname "$0")

wget https://download.ip2location.com/lite/IP2LOCATION-LITE-DB1.BIN.ZIP -O ipv4.zip
rm -f IP2LOCATION-LITE-DB1.BIN
unzip -u ipv4.zip IP2LOCATION-LITE-DB1.BIN

wget https://download.ip2location.com/lite/IP2LOCATION-LITE-DB1.IPV6.BIN.ZIP -O ipv6.zip
rm -f IP2LOCATION-LITE-DB1.IPV6.BIN
unzip -u ipv6.zip IP2LOCATION-LITE-DB1.IPV6.BIN

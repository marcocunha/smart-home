# Hardware

This page described the hardware i'm using. Whenever is possible, I try to use low energy consumption devices. 

## Home Server

The _brain_ of my smart home is a home server based on [Raspberry Pi 4 Model B][pi] with 4GB of RAM onboard. It's a small, affordable, but nonetheless a very capable device. It is protected by an [acrylic case](https://amzn.to/3tNEinS) I bought on Amazon. The case itself helps to disperse the heat. Additionally, it came with 4 heatsinks and a tiny fan.

As storage, I use a [Samsung EVO Plus MicroSD 64GB Class 10 U3](https://amzn.to/3JHjOmt). This card is fast and reliable in handling small I/O operations.

* * *
> Home Assistant team [recommends](https://www.home-assistant.io/installation/raspberrypi#suggested-hardware) to use [Application Class 2](https://www.sdcard.org/developers/overview/application/index.html) as they handle small I/O much more consistently than cards not optimized to host applications. A 32 GB or bigger card is recommended.

* * *

I use the official [Raspberry Pi 15W USB-C Power Supply](https://www.raspberrypi.org/products/type-c-power-supply/) for powering my smart home server. It is important to get enough power for Raspberry Pi to work properly. Home Assistant requires at least 3A power and this power supply cable handles it just right.

## WiFi Network

You're going to have a lot of devices in your network when you have a smart home. It's critical to choose a good router to handle multiple devices and heavy traffic.

<!-- ### Wireless Router

The second most important thing in my smart home is a WiFi router.

I've spent a lot of time choosing _the right router_. My main requirements for the router were:

- **Dual-band: 2.4GHz and 5GHz** — Primarily, I use two networks in my home: 2.4GHz for smart devices and 5GHz for personal devices like phones and laptops. 5GHz uses shorter radio waves, and that provides faster speeds.
- [**MU-MIMO**](https://en.wikipedia.org/wiki/Multi-user_MIMO) — This is a technology that enables simultaneous communication to multiple devices, improving overall speed and enabling network multitasking. It is critical when you have lots of connected devices and want each of them to work with the highest speed.
- [**802.11ac**](https://en.wikipedia.org/wiki/IEEE_802.11ac-2013) — this is a so-called WiFi5 standard. It allows increased speeds and improved scalability. I have a gigabyte connection at my home and wanted to benefit from it.

I chose [ASUS RT-AC1750U](https://www.asus.com/Networking-IoT-Servers/WiFi-Routers/ASUS-WiFi-Routers/RT-AC1750U/) router for my home. It matches every condition above and has nice additional features. Also, I've noticed that routers by ASUS are quite respected among other smart-home enthusiasts.

I'm happy with my decision so far. This router gives the constant 600-900 Mbit/s speed, which is enough to download a 10GB file in less than 2 minutes. -->


### Devices

Below you can find the list of the devices connected to the local network. Most of them have static IP addresses.

| Device                                       | IP                 | HA Integration                |
| -------------------------------------------- | :----------------- | ----------------------------- |
| [Raspberry Pi][pi]                           | `192.168.178.60`\* | –                             |

\* — means the device is connected via Ethernet instead of WiFi to ensure a more reliable connection.

<!-- Devices -->
[pi]: https://www.raspberrypi.org/products/raspberry-pi-4-model-b/


<!-- Integrations -->

## Zigbee Network

My Zigbee devices are connected to Home Assistant via [SONOFF ZBDongle-P Universal Zigbee 3.0 USB Stick Gateway Dongle Plus](https://www.aliexpress.com/item/1005003745323923.html) as a coordinator. Devices are controlled by Home Assistant via: [ZHA](https://www.home-assistant.io/integrations/zha/).


* * *
> I connected my coordinator to the Raspberry Pi through a USB extension cable to avoid interference and improve the connection. This approach is suggested by [zigbee2mqtt documentation](https://www.zigbee2mqtt.io/information/FAQ.html#interview-fails).

* * *

### Devices

| Device                                                         | Quantity | Notes                                            |
| :------------------------------------------------------------- | :------: | :----------------------------------------------- |
| [ZigBee Curtain Module][zigbee-curtain-module]                                          |    9     | To control electric blinds                          |


<!-- Devices -->

[zigbee-curtain-module]: https://www.aliexpress.com/item/1005003919926113.html?

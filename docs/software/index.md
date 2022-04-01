# System Overview

This page describes the software I'm using. I always try to use open-source solutions. 

## [Raspberry Pi OS](https://www.raspberrypi.com/software/)

I use Raspberry Pi OS as a primary OS for my Raspberry Pi. It's basically a Debian variant, so it offers out-of-the-box a lot of useful tools and settings.

## [Docker](https://www.docker.com/)

I use [Docker](https://www.docker.com/) to manage all containers in my smart home. Also whenever I need to add a new tool, I always check if there is a containerized version first. 

Docker allows encapsulating everything related to a single service within a container. This approach helps to maintain the host system clean and manage (start, stop, update and delete) every container separately.

[`docker-compose`](https://docs.docker.com/compose/`) helps to describe my whole setup in a single file and manage it with a few commands.

## [Cockpit](https://cockpit-project.org/)

![Cockpit UI](https://raw.githubusercontent.com/marcocunha/smart-home/main/.github/images/Cockpit.png)

[Cockpit](https://cockpit-project.org/) is a web-based graphical interface for servers.

This tool helps me to manage my infrastructure from a web browser: network, external drives, processes and services, system updates. 

It also includes a terminal that you can access directly from your browser.

## [Home Assistant](https://www.home-assistant.io/)

[Home Assistant](https://www.home-assistant.io) is an open-source home automation platform that puts local control and privacy first.

The community is huge and it allows me to manage everything locally, connecting all my devices, by myself, and it is open source...  What else can you ask for?

The hard choice was related to the type of installation, because as you can see [here](https://www.home-assistant.io/installation/), Home Assistant offers four different installation methods.

After watching this amazing video from the [Home Automation Guy](https://youtu.be/i72K1wyuTfg) I decided to install it as **Home Assistant Container**., Because I had prior knowledge of docker containers, docker-compose, etc., and it provides the flexibility to easily migrate everything to another machine, if eventually I need to upgrade my hardware. 

You can read more about it in [Home Assistant section](./home-assistant/introduction/) of this documentation.

## [alberto](https://github.com/marcocunha/smart-home/blob/main/bin/alberto)

This is just a bash script I wrote for personal needs. You can [find it here](https://github.com/marcocunha/smart-home/blob/main/bin/alberto).

This performs typical tasks I do in my smart home, like bootstrapping, controlling the server, updating, etc.

## Tools

If you use a similar docker-compose and follow the [Getting Started section](./software/getting-started) you will end up with the applications below.

| Application         | URL                                                                |
| ------------------- | :----------------------------------------------------------------- |
| Cockpit             | [https://raspberrypi.local:9090/](https://raspberrypi.local:9090/) |
| Home Assistant      | [http://raspberrypi.local:8123/](http://raspberrypi.local:8123/)   |
| NGinx Proxy Manager | [http://raspberrypi.local:8081/](http://raspberrypi.local:8081/)   |
| Portainer           | [http://raspberrypi.local:9000/](http://raspberrypi.local:9000/)   |
| Duplicati           | [http://raspberrypi.local:8200/](http://raspberrypi.local:8200/)   |

* * *
>Here I'm using raspberrypi.local because it is the default hostname for a typical installation. 
It might be different in your case.

* * *
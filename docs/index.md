---
hide:
  - navigation
---

# Alberto - The smart butler :business_suit_levitating:

=== "Home"

    ![Home](https://user-images.githubusercontent.com/3459374/152371766-1d2a1e17-34d3-4fe6-9e6d-aded02f14de1.png)

=== "Living Room"

    ![Living Room](https://user-images.githubusercontent.com/3459374/152372151-be201bd1-cef9-4ce5-a59d-fd1b534934dc.png){: loading=lazy }

=== "Bedroom"

    ![Bedroom](https://user-images.githubusercontent.com/3459374/152372530-703121d2-2a96-4acc-a664-65109447ab93.png){: loading=lazy }

=== "Balcony"

    ![Baclony](https://user-images.githubusercontent.com/3459374/152372756-a14bbc12-cd40-4549-b93b-6205d8356ce9.png){: loading=lazy }

=== "System"

    ![Living Room](https://user-images.githubusercontent.com/3459374/152374825-4e564a75-7c8d-4001-b71a-00dcd5291e73.png){: loading=lazy }

[![GitHub Workflow Status](https://github.com/marcocunha/smart-home/actions/workflows/pages/pages-build-deployment/badge.svg?branch=main)](https://github.com/marcocunha/smart-home/actions/workflows/pages/pages-build-deployment)
[![Last Commit][last-commit-img]][github-url]
[![Commit Activity][commit-activity-img]][github-url]
[![License][license-img]][license-url]
[![GitHub Stars][stars-img]][github-url]
[![Twitter Followers][twitter-img]][twitter-url]

This is my personal Home Assistant configuration, to try to make my life easier and my home more confortable. 

I hope this will also help you get some inspiration to build your own smart home.

**Alberto** is the name of my smart home system. 

Why Alberto? Just because I think it is a funny name and sounds appropriate for a smart-home assistant/butler name 😁

The best way to discover new ideas and inspire is by [reading the code][github-url], copying-pasting parts of my configuration and adjusting it to your needs.

Read this documentation to see the bigger picture:

[Hardware](./hardware){: .md-button }
[Software](./software/system){: .md-button }
[Home Assistant](./home-assistant/introduction){: .md-button }
[Resources](./resources){: .md-button }

## What's inside?

My home setup for those who are too lazy to read everything:

- [Raspberry Pi 4B](https://www.raspberrypi.org/products/raspberry-pi-4-model-b/) as a home server.
- [Home Assistant](https://home-assistant.io) for home automations.
- [Mosquitto](https://mosquitto.org/) and [zigbee2mqtt](https://www.zigbee2mqtt.io/) for Zigbee devices.
- Reverse proxy using [Nginx Proxy Manager](https://nginxproxymanager.com/) with [CloudFlare](https://www.cloudflare.com/).
- [AdGuard Home](https://github.com/AdguardTeam/AdGuardHome) for network-level ad-blocking.


## Motivation

I write this documentation for two main reasons:

1. **To keep track of growing my smart home.** To maintain an understanding of how things are working.
2. **To help other enthusiasts inspire.** People often ask about my smart home setup. Now I can give them a link to this documentation, instead of explaining everything once again.

## Future Plans

I have a [public Notion board](https://www.notion.so/denysdovhan/f09ea06da5db4cfa84d3ca50417b93b2?v=5fccab53c2fd4ac188ee0b92c2ca1cb9) with ideas and tasks for my smart home. You can follow and comment my plans there.

## License

[MIT][license-url] © [Marco Cunha][marcocunha]

<!-- References -->

[github-url]: https://github.com/marcocunha/smart-home
[github-img]: https://img.shields.io/github/workflow/status/marcocunha/smart-home/CI/master?style=flat-square
[last-commit-img]: https://img.shields.io/github/last-commit/marcocunha/smart-home?style=flat-square
[commit-activity-img]: https://img.shields.io/github/commit-activity/m/marcocunha/smart-home?style=flat-square
[license-url]: https://github.com/marcocunha/smart-home/blob/master/LICENSE
[license-img]: https://img.shields.io/github/license/marcocunha/smart-home?style=flat-square
[twitter-url]: https://twitter.com/MarcoCunha27
[twitter-img]: https://img.shields.io/twitter/follow/MarcoCunha27?label=Follow
[stars-img]: https://img.shields.io/github/stars/marcocunha/smart-home?style=social
[denysdovhan]: https://denysdovhan.com
[marcocunha]: https://mcunha.engineer
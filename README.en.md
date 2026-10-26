<h1 align="center">Guangxi University Campus Map</h1>

<p align="center"><a href="README.md">简体中文</a> · <strong>English</strong></p>

An interactive 3D map of Guangxi University's main campus on Daxue East Road, built with Three.js, Blender, and React using OpenStreetMap data and public sources.

**[Explore online](https://wcqqq1214.github.io/gxu-campus-3d/)**

![Campus overview and place list](docs/screenshots/readme/overview.jpg)

## Features

- Search campus places and buildings, switch viewpoints, and follow a campus tour.
- Choose morning, day, dusk, or night lighting; adjust map layers and rendering quality.
- Share the current view or export a PNG with OpenStreetMap attribution.
- Use mobile and keyboard controls, with support for system reduced-motion preferences.

<details>
<summary>More screenshots: lighting, close-ups, and mobile</summary>

| Morning | Daytime |
| --- | --- |
| ![Library in morning light](docs/screenshots/readme/library-morning.jpg) | ![Library in daylight](docs/screenshots/readme/library-day.jpg) |
| Dusk | Night |
| ![Library at dusk](docs/screenshots/readme/library-evening.jpg) | ![Library at night](docs/screenshots/readme/library-night.jpg) |
| North side of the library | Road beneath Chongzuo Bridge |
| ![North side and entrance of the library](docs/screenshots/readme/library-north.jpg) | ![Road beneath Chongzuo Bridge](docs/screenshots/readme/chongzuo-bridge.jpg) |
| Mobile place details | Mobile tools |
| ![Teaching Building 6 on mobile](docs/screenshots/readme/mobile-detail.jpg) | ![Mobile tools menu](docs/screenshots/readme/mobile-tools.jpg) |

![Basketball courts west of the east athletics field](docs/screenshots/readme/basketball-east.jpg)

</details>

Overview captured on 2026-10-27; other screenshots on 2026-10-12. All use local static `dev` builds, with simulated mobile viewports. The live site may differ.

## Run locally

Use Node.js 24. No map API key or backend service is required.

```sh
git clone --branch dev https://github.com/wcqqq1214/gxu-campus-3d.git
cd gxu-campus-3d
npm ci
npm run dev
```

Open the Local URL shown in the terminal. Run `npm run build:pages` to build into `out/`, then `npm run preview` to serve it at <http://127.0.0.1:4300/gxu-campus-3d/>.

## Data and documentation

The model covers the east, west, and north campus areas. It is not based on an on-site survey; some heights, facades, and layouts are estimated. Documentation is in Chinese:

- [Data sources and accuracy](docs/DATA.md)
- [Model structure, tests, and rebuilding](docs/MODELING.md) (Blender source files are not distributed; the website runs without them)
- [Interface and interactions](docs/DESIGN.md)

Original code, documentation, models, materials, and renders are [MIT-licensed](LICENSE). OpenStreetMap geographic databases and derived databases use ODbL, with attribution to **© OpenStreetMap contributors**. See the [third-party notices](licenses/THIRD_PARTY.md) for other resources. Reference photos and videos are not distributed.

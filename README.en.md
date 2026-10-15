<h1 align="center">Guangxi University Campus Map</h1>

<p align="center">
  <a href="README.md">简体中文</a> · <strong>English</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Three.js-000000?style=flat&amp;logo=threedotjs&amp;logoColor=white" alt="Three.js">
  <img src="https://img.shields.io/badge/Blender-E87D0D?style=flat&amp;logo=blender&amp;logoColor=white" alt="Blender">
  <img src="https://img.shields.io/badge/React-20232A?style=flat&amp;logo=react&amp;logoColor=61DAFB" alt="React">
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat&amp;logo=typescript&amp;logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/OpenStreetMap-387C44?style=flat&amp;logo=openstreetmap&amp;logoColor=white" alt="OpenStreetMap">
</p>

<p align="center">
  A browser-based 3D map of Guangxi University's main campus on Daxue East Road, built with Three.js, Blender, OpenStreetMap data, and public sources.
</p>

<p align="center">
  <a href="https://wcqqq1214.github.io/gxu-campus-3d/">Explore online</a>
</p>

![Campus overview and places grouped by category](docs/screenshots/readme/overview.jpg)

## Features

- Find 20 featured places and about 300 named campus buildings, explore buildings from different angles, and take a guided campus tour.
- Switch between morning, day, dusk, and night; toggle map layers and adjust rendering quality.
- Share a link to your current view or export a PNG with OpenStreetMap attribution.
- Use desktop or mobile controls, keyboard navigation, and system reduced-motion preferences.

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

Captured on 2026-10-12 from a local `dev` build with automatic quality and simulated mobile viewports. The live site may differ.

## Model coverage

The model covers the east, west, and north campus areas: 446 campus buildings and building volumes, 13 surrounding buildings, and 2,936 illustrative trees. It is not based on an on-site survey; some heights, facades, and layouts are estimated. See the [data notes](docs/DATA.md).

## Run locally

Use Node.js 24. No map API key or backend service is required.

```sh
git clone --branch dev https://github.com/wcqqq1214/gxu-campus-3d.git
cd gxu-campus-3d
npm ci
npm run dev
```

Open the Local URL shown in the terminal. To check, build, and preview:

```sh
npm run typecheck
npm run lint
npm test
npm run build:pages
npm run preview
```

The static build is saved to `out/` and served at `http://127.0.0.1:4300/gxu-campus-3d/` by the preview command. Push development commits to `origin/dev`; updates to `main` require explicit authorization.

## Documentation and licensing

Documentation is in Chinese:

- [Data sources and accuracy](docs/DATA.md)
- [Model structure, data tests, and rebuilding](docs/MODELING.md) (Blender source files are not distributed; the website runs without them)
- [Interface and interactions](docs/DESIGN.md)

Original code, documentation, models, materials, and renders are [MIT-licensed](LICENSE). OpenStreetMap geographic databases and derived databases use ODbL, with attribution to **© OpenStreetMap contributors**. See the [third-party notices](licenses/THIRD_PARTY.md) for other resources. Official photos and videos are used only as modeling references and are not distributed.

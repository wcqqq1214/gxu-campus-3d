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
  A 3D map of Guangxi University's main campus on Daxue East Road. Built with Three.js and Blender using OpenStreetMap and publicly available references, it lets you find places, explore buildings, tour the campus, and switch between day and night in your browser.
</p>

<p align="center">
  <a href="https://wcqqq1214.github.io/gxu-campus-3d/">Explore online</a>
</p>

![Campus overview and places grouped by category](docs/screenshots/readme/overview.jpg)

## Features

- Find and browse 20 selected places with categories, Chinese alias search, and linked list and map highlights.
- Explore freely with multiple viewing angles or follow a campus tour, with options to pause, resume, and skip stops.
- Switch between morning, daytime, dusk, and night; toggle buildings, trees, roads, and other layers. Quality adapts automatically to performance.
- Share a link to the current view or export a PNG with OpenStreetMap attribution.
- Use the map on mobile, with keyboard navigation and support for the system's reduced-motion preference.

| Place details on mobile | Mobile tools menu |
| --- | --- |
| ![Summary of Teaching Building 6 on mobile](docs/screenshots/readme/mobile-detail.jpg) | ![More tools menu on mobile](docs/screenshots/readme/mobile-tools.jpg) |

## Model coverage

| Campus buildings | Surrounding buildings | Selected landmarks | Schematic trees |
| :---: | :---: | :---: | :---: |
| 446 buildings / volumes | 13 buildings | 20 places | 2,936 trees |

Built from OpenStreetMap and public references, the model covers the east, west, and north campus areas. It has not been verified by an on-site survey, and some building heights, facades, and facility layouts are estimates. See the [data notes](docs/DATA.md) for details.

<details>
<summary>More screenshots</summary>

| North side of the library | Road beneath Chongzuo Bridge |
| --- | --- |
| ![North side and entrance of the library](docs/screenshots/readme/library-north.jpg) | ![Road and sidewalks beneath Chongzuo Bridge](docs/screenshots/readme/chongzuo-bridge.jpg) |

![Basketball court models west of the east athletics field](docs/screenshots/readme/basketball-east.jpg)

</details>

Screenshots were captured from a development version on 2026-10-07 and may differ from the live site.

## Run locally

Use Node.js 24 to match CI.

```sh
git clone https://github.com/wcqqq1214/gxu-campus-3d.git
cd gxu-campus-3d
npm ci
npm run dev
```

Open the Local URL printed in your terminal. The project uses React, TypeScript, vinext, and Vite. Running the website requires no map API key or backend service.

### Checks and static build

```sh
npm run typecheck
npm run lint
npm test
npm run build:pages
npm run preview
```

Static files are generated in `out/`. The default preview URL is `http://127.0.0.1:4300/gxu-campus-3d/`. Serve the files over HTTP instead of opening the HTML files directly.

Pushes to `main` and pull requests targeting `main` run checks and builds. Pages deployment runs only on pushes to the main branch and manual workflow runs.

### Data tests and model rebuilding

See the [modeling guide](docs/MODELING.md) for data tests and model rebuilding. The editable Blender source is not included in the repository and is not currently available for download. Running the website and standard tests does not require it.

## Project documentation

The following documents are in Chinese:

- [Data sources and accuracy](docs/DATA.md)
- [Model structure and rebuilding](docs/MODELING.md)
- [Interface and interactions](docs/DESIGN.md)

## Licensing

Code is licensed under [MIT](LICENSE). Original models and materials are licensed under [CC BY 4.0](licenses/MODELS.md). The geographic database and its derivative data are licensed under ODbL, with attribution to **© OpenStreetMap contributors**. See the [third-party notices](licenses/THIRD_PARTY.md) for other data and font licenses.

Official photographs and videos are used only as modeling references. They are not distributed as website textures or repository images.

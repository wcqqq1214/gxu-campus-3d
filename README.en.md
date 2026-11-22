<h1 align="center">Guangxi University Campus Map</h1>

<p align="center"><a href="README.md">简体中文</a> · <strong>English</strong></p>

An interactive 3D map of Guangxi University's main campus on Daxue East Road. Geographic footprints come from OpenStreetMap, key buildings and landmarks are modeled in Blender from public sources, and the web app runs on Three.js and React.

**[Explore online](https://wcqqq1214.github.io/gxu-campus-3d/)**

![Campus overview and place list](docs/screenshots/readme/overview.jpg)

## Features

- Search campus landmarks and named buildings, switch viewpoints, or take a guided tour.
- Switch between Morning, Day, Evening, and Night lighting, toggle map layers, and adjust graphics quality.
- Share a link to your current view or export a PNG screenshot with OpenStreetMap attribution.
- Works with touch, mouse, and keyboard navigation, and respects system reduced-motion settings.

<details>
<summary>More screenshots: lighting, close-ups, and mobile</summary>

| Morning | Day |
| --- | --- |
| ![Library in morning light](docs/screenshots/readme/library-morning.jpg) | ![Library in daylight](docs/screenshots/readme/library-day.jpg) |
| Evening | Night |
| ![Library at dusk](docs/screenshots/readme/library-evening.jpg) | ![Library at night](docs/screenshots/readme/library-night.jpg) |
| North side of the library | Road beneath Chongzuo Bridge |
| ![North side and entrance of the library](docs/screenshots/readme/library-north.jpg) | ![Road beneath Chongzuo Bridge](docs/screenshots/readme/chongzuo-bridge.jpg) |
| Mobile place details | Mobile tools |
| ![Teaching Building 6 on mobile](docs/screenshots/readme/mobile-detail.jpg) | ![Mobile tools menu](docs/screenshots/readme/mobile-tools.jpg) |

![Basketball courts west of the east athletics field](docs/screenshots/readme/basketball-east.jpg)

</details>

> Overview captured on 2026-10-27; the rest on 2026-10-12 from local `dev` static builds (with simulated mobile viewports), so details may differ slightly from the live site.

## Run locally

This project uses Node.js 24 (pinned in [.nvmrc](.nvmrc) and matched in CI; with nvm, run `nvm install && nvm use`). No map API key or backend service is needed:

```sh
git clone --branch dev https://github.com/wcqqq1214/gxu-campus-3d.git
cd gxu-campus-3d
npm ci
npm run dev
```

Open the Local URL printed in your terminal. To generate and preview a static build locally:

```sh
npm run build:pages   # Build static assets into out/
npm run preview       # Serve at http://127.0.0.1:4300/gxu-campus-3d/
```

### Checks and tests

- **Frontend checks**: `npm run check` runs TypeScript type checking, oxlint, and JS/TS unit tests. CI runs `npm run typecheck:fast` immediately after installing npm dependencies to catch type errors early with tsrs. You can also run it locally.
- **Python checks**: Python is pinned to 3.12 in [.python-version](.python-version). After installing the dev dependencies, run `npm run lint:python` for Ruff checks and `npm run format:python` to format.
- **Browser regressions**: Install Chromium with `npx playwright install chromium`, then run `npm run test:browser` to test menus, cameras, and the bilingual interface.

Pushes to `dev` run these checks in CI along with Python data tests, Blender geometry regressions, and the static build (without deploying). See [model structure, tests, and rebuilding](docs/MODELING.md) for full setup details.

## Data and documentation

The model covers the east, west, and north campus areas. It is not based on an on-site survey; some heights, facades, and layouts are estimated from public sources. Documentation is in Chinese:

- [Data sources and accuracy](docs/DATA.md)
- [Model structure, tests, and rebuilding](docs/MODELING.md) (Blender source files are not distributed; the website runs without them)
- [Interface and interactions](docs/DESIGN.md)

Original code, documentation, models, materials, and renders are [MIT-licensed](LICENSE). OpenStreetMap geographic databases and derived databases are licensed under ODbL with attribution to **© OpenStreetMap contributors**. See [third-party notices](licenses/THIRD_PARTY.md) for other assets. Reference photos and videos are not distributed.

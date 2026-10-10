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

- Browse 20 selected places grouped into academic buildings, sports and culture, gates, roads and bridges, and daily life. Search supports Chinese aliases such as “六教” and “新东园门”, with results shown in a flat list.
- Place entries and map markers highlight each other. Their numbers match the tour stops, making it easy to locate places in the list and the scene.
- Place details include an introduction, viewing angles, and sharing options. The horizontally scrollable view bar offers overview, overhead, orbit, front, rear, and close-up views. You can also rotate, pan, and zoom freely.
- Tour controls stay at the bottom of the panel, with options to pause, resume, and skip stops, plus progress for each 8.5-second stop. Pause and resume remain available when the panel is collapsed.
- Choose morning, daytime, dusk, or night lighting. Automatic quality adjusts shadows, trees, and close-up details based on runtime performance.
- Toggle campus buildings, trees, roads and bridges, water, sports grounds, surrounding buildings, the campus boundary, and place names independently.
- Use the Share menu to copy a link to the current view or export a PNG with OpenStreetMap attribution.
- On phones, a bottom panel supports summary, detail, and collapsed states. More tools brings together viewing angles, sharing, and controls help. Keyboard navigation and the system's reduced-motion preference are supported.

| Place details on mobile | Mobile tools menu |
| --- | --- |
| ![Summary of Teaching Building 6 on mobile](docs/screenshots/readme/mobile-detail.jpg) | ![More tools menu on mobile](docs/screenshots/readme/mobile-tools.jpg) |

## Model coverage

| Campus buildings | Surrounding buildings | Selected landmarks | Schematic trees |
| :---: | :---: | :---: | :---: |
| 446 buildings / volumes | 13 buildings | 20 places | 2,936 trees |

The model covers the east, west, and north campus areas, including two athletics fields, 31 outdoor basketball courts, Nongyuan Road, and three major bridges with roads passing beneath them. A white line marks the approximate campus boundary, and Nongyuan Road is represented as a public road. Off-campus buildings are limited to those immediately adjacent to the boundary, within roughly 20 meters.

| North side of the library | Road beneath Chongzuo Bridge |
| --- | --- |
| ![North side and entrance of the library](docs/screenshots/readme/library-north.jpg) | ![Road and sidewalks beneath Chongzuo Bridge](docs/screenshots/readme/chongzuo-bridge.jpg) |

![Basketball court models west of the east athletics field](docs/screenshots/readme/basketball-east.jpg)

Screenshots were updated on 2026-10-07 using a local development version of the `dev` branch, including the latest place-detail changes. They may be ahead of the live site. Mobile screenshots were captured in a desktop browser at a 390 × 844 viewport. Screenshot dates, versions, and viewing angles are recorded locally.

Building footprints primarily come from an **OpenStreetMap snapshot dated 2026-09-09**. Roads and bridges use supplementary data retrieved on 2026-09-11. Building appearances draw on public photographs and references from different years; those dates do not establish current conditions. This is an independent open-source project and has not been verified by an on-site campus survey.

334 building records still use default heights for their building type. Other heights are calculated from documented floor counts and estimated floor heights, and should not be treated as measurements. The campus count includes 11 additional building and connecting-corridor volumes in the north campus area, so it does not represent only standalone buildings. Facades not covered by photographs, tree positions, and some facility layouts also involve inference. Of the basketball courts, 16 use map-derived positions, while another 15 in the east campus area use estimated layouts based on references. See the [data notes](docs/DATA.md) and [source records](public/data/sources.json) for evidence and limitations.

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

Data tests use Python 3.12:

```sh
python3.12 -m venv work/data-venv
source work/data-venv/bin/activate
python -m pip install -r scripts/requirements.txt -c scripts/constraints-geodata.txt
npm run test:data
```

The editable Blender source is stored locally at `blender/gxu-campus.blend`, with named objects, materials, and packed textures. It is no longer tracked in Git, and no Release download is currently available. Running the website and standard tests does not require this file. Incremental model changes and source-model checks require the local source file and Blender; see the [modeling guide](docs/MODELING.md). [Raw data snapshots](data/snapshots/) support offline restoration. [Web models](public/models/) use Draco compression and load on demand. The asset manifest and tests keep the initial model payload below 6 MB (decimal), excluding scripts, JSON, and decoders.

## Project documentation

The following documents are in Chinese:

- [Data sources and accuracy](docs/DATA.md)
- [Model structure and rebuilding](docs/MODELING.md)
- [Interface and interactions](docs/DESIGN.md)

Development notes, acceptance reports, and screenshots are kept locally and are not distributed with the repository, except for baseline data required by tests and validation, and the screenshots shown in the READMEs.

## Licensing

Code is licensed under [MIT](LICENSE). Original models and materials are licensed under [CC BY 4.0](licenses/MODELS.md). The geographic database and its derivative data are licensed under ODbL, with attribution to **© OpenStreetMap contributors**. See the [third-party notices](licenses/THIRD_PARTY.md) for other data and font licenses.

Official photographs and videos are used only as modeling references. They are not distributed as website textures or repository images.

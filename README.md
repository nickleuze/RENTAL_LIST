# RENTAL_LIST

A clean, lightweight static catalog for rentable equipment.

## Current v1 scope

- Static web catalog for a hosted public URL, suitable for GitHub Pages or similar static hosting.
- Inventory source: a local `Rental-Database.xlsm` workbook, or any workbook path passed via `INVENTORY_XLSM`.
- Public item data comes from the `Rental-Database` sheet.
- Category tabs use the section/header rows above each group in the workbook.
- Category tab order is controlled by `data/category-order.json`.
- Client-visible price is `VK (Netto)` only.
- The `Kits` sheet is deferred for a later milestone.

## Commands

```bash
make build       # convert the workbook to data/inventory.json
make check       # validate conversion and JSON output
make serve       # rebuild and preview locally at http://localhost:8000
make watch       # rebuild data/inventory.json whenever the workbook changes
make dev         # serve locally and watch Excel changes in one process
make docker-up   # run the dev server/watcher in Docker at http://localhost:8888
make docker-down # stop the Docker container
make pages-build # package the committed static site into dist/ for GitHub Pages
make clean       # remove generated data/inventory.json
```

The project uses only the Python standard library for the conversion script. There is no package install step.

## Updating the catalog

### Option A: Docker dev server

```bash
make docker-up
```

Open `http://localhost:8888`. The container serves the site and watches the workbook mounted read-only at `/inventory/Rental-Database.xlsm`. By default Docker looks for `./Rental-Database.xlsm`; to use another local path, run `INVENTORY_XLSM=/path/to/Rental-Database.xlsm make docker-up`. When you edit/save the workbook on your machine, Docker rebuilds `data/inventory.json`; refresh the browser to see the update.

Stop it with:

```bash
make docker-down
```

### Option B: Local Python dev server

```bash
make dev
```

This does the same thing without Docker: serves the site and watches Excel changes in one process.

### Manual flow

Without the watcher, run `make build` after editing the workbook, then refresh the browser. Before committing/deploying, run `make check`.

## Changing category tab order

Edit `data/category-order.json` and put the category names in the order you want them to appear. Keep the names exactly the same as the category tab labels. Any category missing from the file is still shown after your ordered categories, sorted alphabetically.

After editing the order, refresh the browser. Before committing/deploying, run `make check`.

## GitHub Pages deployment

This repo includes a GitHub Actions workflow at `.github/workflows/deploy-pages.yml`. On pushes to `main` or `master`, it publishes only the static site files from `dist/`:

- `index.html`
- `assets/`
- `data/inventory.json`

The source workbook is intentionally ignored by Git and not published. To update the public catalog, edit/save the workbook, run `make check`, commit the regenerated `data/inventory.json`, and push.

In GitHub, set **Settings → Pages → Build and deployment → Source** to **GitHub Actions**.

## Files

- `index.html` — catalog page.
- `assets/styles.css` — responsive styling.
- `assets/app.js` — search/filter rendering.
- `scripts/convert_inventory.py` — XLSM-to-JSON converter.
- `data/inventory.json` — generated catalog data.
- `data/category-order.json` — editable category tab order.

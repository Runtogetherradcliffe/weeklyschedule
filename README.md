# Strava Routes Cache + GitHub Pages Map

This starter kit lets you:
- Fetch all your **Strava routes** and cache them as **GeoJSON** in `/routes/`
- Build a `routes/index.json` with route metadata (name, distance, type, bbox, etc.)
- Serve a **Leaflet map** from GitHub Pages (`/web/routes-map`) to browse/display routes
- Keep everything fresh via **GitHub Actions** (manual or scheduled)

## How it works

1. **`scripts/strava_cache.py`** authenticates using your Strava OAuth **refresh token**, fetches all of your routes, 
   writes each as `routes/strava_route_<id>_<slug>.geojson`, and builds `routes/index.json`.
2. **GitHub Actions** (`.github/workflows/update_routes.yml`) runs the script on demand or nightly and commits any changes. 
3. **`web/routes-map`** is a static Leaflet app that loads `routes/index.json` and lets you preview each route on a map.

> Distances are shown in kilometres.

## Setup (one-time)

1. Add these **repository secrets** in GitHub (Settings → Secrets and variables → Actions):
   - `STRAVA_CLIENT_ID`
   - `STRAVA_CLIENT_SECRET`
   - `STRAVA_REFRESH_TOKEN`
2. Commit this folder structure to your repo (same one that powers your GitHub Pages site).
3. Ensure GitHub Pages serves from the repo root (or `main` branch) so `/web/routes-map` is accessible.
4. (Optional) Link to the map page from your site navigation: `/web/routes-map/`

## Run locally (optional)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/strava_cache.py
# Check the /routes folder and /routes/index.json
```

## Trigger a refresh in GitHub
- Go to **Actions → Update Strava Routes Cache → Run workflow**.
- Or wait for the nightly schedule.

## Streamlit integration
Your Streamlit app can read `/routes/index.json` directly and display selected routes using `pydeck`, `folium`, or similar.
This gives you a **single source of truth** for route geometry that both GitHub Pages and Streamlit can use.


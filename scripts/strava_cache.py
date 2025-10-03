#!/usr/bin/env python3
import os
import re
import json
import time
import math
import hashlib
import unicodedata
from datetime import datetime, timezone

import requests

STRAVA_API = "https://www.strava.com/api/v3"
ROUTES_DIR = os.environ.get("ROUTES_DIR", "routes")
INDEX_PATH = os.environ.get("INDEX_PATH", os.path.join(ROUTES_DIR, "index.json"))

# --- Utilities ---

def slugify(value: str) -> str:
    value = str(value)
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[-\s]+", "-", value)
    return value[:60] or "route"

def decode_polyline(polyline_str):
    """Decodes a polyline that has been encoded using Google's algorithm.
    Returns a list of (lat, lon) pairs.
    """
    coords = []
    index, lat, lng = 0, 0, 0
    length = len(polyline_str)

    while index < length:
        # Decode latitude
        result, shift = 0, 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += dlat

        # Decode longitude
        result, shift = 0, 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result >> 1) if (result & 1) else (result >> 1)
        lng += dlng

        coords.append((lat / 1e5, lng / 1e5))
    return coords

def bbox_from_coords(coords):
    lats = [c[0] for c in coords]
    lngs = [c[1] for c in coords]
    return [min(lngs), min(lats), max(lngs), max(lats)]  # [minx, miny, maxx, maxy]

def center_from_bbox(b):
    minx, miny, maxx, maxy = b
    return [(minx + maxx) / 2.0, (miny + maxy) / 2.0]

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def km(meters: float) -> float:
    return round((meters or 0.0) / 1000.0, 3)

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

# --- Strava OAuth ---

def get_access_token():
    client_id = os.environ["STRAVA_CLIENT_ID"]
    client_secret = os.environ["STRAVA_CLIENT_SECRET"]
    refresh_token = os.environ["STRAVA_REFRESH_TOKEN"]

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    r = requests.post("https://www.strava.com/oauth/token", data=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["access_token"]

def api_get(path, token, params=None):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{STRAVA_API}{path}", headers=headers, params=params or {}, timeout=30)
    if r.status_code == 429:
        raise RuntimeError("Rate limited by Strava (HTTP 429). Try again later or reduce frequency.")
    r.raise_for_status()
    return r.json()

# --- Fetch routes ---

def get_athlete(token):
    return api_get("/athlete", token)

def list_athlete_routes(athlete_id, token, per_page=200, max_pages=10):
    routes = []
    for page in range(1, max_pages + 1):
        data = api_get(f"/athletes/{athlete_id}/routes", token, params={"page": page, "per_page": per_page})
        if not data:
            break
        routes.extend(data)
        if len(data) < per_page:
            break
    return routes

def get_route_detail(route_id, token):
    return api_get(f"/routes/{route_id}", token)

# --- GeoJSON ---

def polyline_to_geojson_feature(coords, properties=None):
    # GeoJSON expects [lon, lat]
    line = [[lon, lat] for lat, lon in coords]
    return {
        "type": "Feature",
        "properties": properties or {},
        "geometry": {"type": "LineString", "coordinates": line},
    }

# --- Main caching logic ---

def main():
    ensure_dir(ROUTES_DIR)
    token = get_access_token()

    athlete = get_athlete(token)
    athlete_id = athlete["id"]

    routes = list_athlete_routes(athlete_id, token)
    print(f"Found {len(routes)} routes for athlete {athlete_id}")

    index = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "athlete_id": athlete_id,
        "count": 0,
        "routes": [],
    }

    for r in routes:
        route_id = r["id"]
        name = r.get("name") or f"Route {route_id}"
        slug = slugify(name)
        distance_m = r.get("distance", 0.0)  # meters
        elev_gain_m = r.get("elevation_gain", 0.0)
        route_type = r.get("type")  # 'ride' or 'run'
        updated_at = r.get("updated_at") or r.get("created_at")

        # Prefer detailed route to get full polyline if available
        try:
            detail = get_route_detail(route_id, token)
            mp = (detail.get("map") or {}).get("polyline") or (detail.get("map") or {}).get("summary_polyline")
            # Some responses use 'map': {'summary_polyline': ...}
            if not mp:
                mp = (r.get("map") or {}).get("polyline") or (r.get("map") or {}).get("summary_polyline")
        except Exception as e:
            print(f"Warning: could not fetch detail for route {route_id}: {e}")
            mp = (r.get("map") or {}).get("polyline") or (r.get("map") or {}).get("summary_polyline")

        if not mp:
            print(f"Skipping route {route_id} (no polyline)")
            continue

        coords = decode_polyline(mp)
        if not coords:
            print(f"Skipping route {route_id} (empty decoded coords)")
            continue

        bbox = bbox_from_coords(coords)
        center = center_from_bbox(bbox)

        props = {
            "id": route_id,
            "name": name,
            "slug": slug,
            "type": route_type,
            "distance_m": float(distance_m),
            "distance_km": km(distance_m),
            "elev_gain_m": float(elev_gain_m or 0.0),
            "updated_at": updated_at,
        }

        feature = polyline_to_geojson_feature(coords, props)
        gj = {"type": "FeatureCollection", "features": [feature], "bbox": bbox}

        # Use a stable filename that survives renames by keeping the id
        filename = f"strava_route_{route_id}_{slug}.geojson"
        path = os.path.join(ROUTES_DIR, filename)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(gj, f, ensure_ascii=False, indent=2)

        index["routes"].append({
            "id": route_id,
            "name": name,
            "slug": slug,
            "type": route_type,
            "distance_m": float(distance_m),
            "distance_km": km(distance_m),
            "elev_gain_m": float(elev_gain_m or 0.0),
            "file": f"routes/{filename}",
            "bbox": bbox,
            "center": center,
            "updated_at": updated_at,
        })

    index["count"] = len(index["routes"])
    index["routes"].sort(key=lambda x: (x["type"] or "", x["name"] or ""))

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"Wrote {index['count']} routes to {ROUTES_DIR} and index to {INDEX_PATH}")

if __name__ == "__main__":
    main()

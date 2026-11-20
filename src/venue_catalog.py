"""
Venue and Hospital Catalog for Greater Hyderabad.
Manages verified locations, coordinates, hospital corridors, and road network retrieval.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
NETWORKS_DIR = DATA_DIR / "networks"
VENUES_CSV = DATA_DIR / "hyderabad_venues.csv"
HOSPITALS_CSV = DATA_DIR / "hyderabad_hospitals.csv"
UPPAL_GRAPHML = DATA_DIR / "uppal_road_network.graphml"


def load_venues() -> pd.DataFrame:
    """Load verified Hyderabad venues catalog."""
    if VENUES_CSV.exists():
        return pd.read_csv(VENUES_CSV)
    return pd.DataFrame(columns=[
        "Venue_Key", "Venue_Name", "Commissionerate", "Area",
        "Latitude", "Longitude", "Capacity", "Default_Hospital", "Source"
    ])


def load_hospitals() -> pd.DataFrame:
    """Load verified Hyderabad emergency referral hospitals."""
    if HOSPITALS_CSV.exists():
        return pd.read_csv(HOSPITALS_CSV)
    return pd.DataFrame(columns=[
        "Hospital_Name", "Zone", "Latitude", "Longitude", "Source"
    ])


def get_venue(venue_key: str) -> dict[str, Any] | None:
    """Get venue record by key."""
    df = load_venues()
    if df.empty:
        return None
    matches = df[df["Venue_Key"] == venue_key]
    if not matches.empty:
        return matches.iloc[0].to_dict()
    return None


def get_hospital(hospital_name: str) -> dict[str, Any] | None:
    """Get hospital record by name."""
    df = load_hospitals()
    if df.empty:
        return None
    h_clean = str(hospital_name).strip().lower()
    matches = df[df["Hospital_Name"].astype(str).str.strip().str.lower() == h_clean]
    if not matches.empty:
        return matches.iloc[0].to_dict()
    return None


def geocode_custom_location(query: str) -> tuple[float, float, str] | None:
    """
    Safely look up coordinates for a user-specified location in Hyderabad via OpenStreetMap Nominatim.
    Returns (lat, lon, display_name) or None if not found or unreachable.
    Never invents coordinates.
    """
    if not query or not query.strip():
        return None
    try:
        import requests
        headers = {"User-Agent": "traffic_copilot_location_lookup"}
        q = f"{query.strip()}, Hyderabad, India"
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": q, "format": "json", "limit": 1},
            headers=headers,
            timeout=5
        )
        if resp.status_code == 200:
            results = resp.json()
            if results and len(results) > 0:
                lat = float(results[0]["lat"])
                lon = float(results[0]["lon"])
                addr = str(results[0].get("display_name", query))
                return lat, lon, addr
    except Exception:
        pass
    return None


def get_road_network_path(venue_key: str, lat: float | None = None, lon: float | None = None, dist_m: int = 3000) -> Path:
    """
    Returns path to graphml for the given venue.
    If cached in data/networks/<venue_key>.graphml, returns that.
    If Uppal stadium, returns data/uppal_road_network.graphml.
    If not yet cached, attempts download via OSMnx; if offline/fails, falls back to UPPAL_GRAPHML.
    """
    NETWORKS_DIR.mkdir(parents=True, exist_ok=True)
    if venue_key == "uppal_stadium" and UPPAL_GRAPHML.exists():
        return UPPAL_GRAPHML

    cached_file = NETWORKS_DIR / f"{venue_key}.graphml"
    if cached_file.exists():
        return cached_file

    # Attempt download if coordinates provided
    if lat is not None and lon is not None:
        try:
            import osmnx as ox
            print(f"Downloading road network for {venue_key} ({lat}, {lon}) within {dist_m}m...")
            G = ox.graph_from_point((lat, lon), dist=dist_m, network_type="drive", simplify=True)
            ox.save_graphml(G, filepath=cached_file)
            return cached_file
        except Exception as e:
            print(f"OSM download failed for {venue_key} ({e}). Falling back to existing Uppal network.")

    # Fallback to default Uppal road network
    return UPPAL_GRAPHML


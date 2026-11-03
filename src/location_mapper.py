import os
import time
import math
import osmnx as ox
import pandas as pd

GRAPH_PATH = "data/uppal_road_network.graphml"
OUTPUT_PATH = "outputs/location_mapping.csv"

SEARCH_RADIUS = 3000       # 3 km
MAX_SNAP_DISTANCE = 250    # Maximum acceptable distance to a road


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate straight-line distance between two coordinates."""

    R = 6371000

    lat1, lon1, lat2, lon2 = map(
        math.radians, [lat1, lon1, lat2, lon2]
    )

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    return 2 * R * math.asin(math.sqrt(a))

def map_locations():

    print("\n========== HYDERABAD LOCATION MAPPING ==========")

    # Load existing road network
    if not os.path.exists(GRAPH_PATH):
        print("Road network file not found!")
        return

    G = ox.load_graphml(GRAPH_PATH)

    print("Road network loaded successfully!")
    print("Total Nodes:", len(G.nodes))
    print("Total Edges:", len(G.edges))

    # Reference location
    center_place = (
        "Rajiv Gandhi International Cricket Stadium, "
        "Uppal, Hyderabad, India"
    )

    center_lat, center_lon = ox.geocode(center_place)

    print("\nReference Location: Uppal Stadium")
    print("Latitude:", center_lat)
    print("Longitude:", center_lon)

    # Candidate locations to investigate
    locations = [
        "Uppal Metro Station, Hyderabad, India",
        "Uppal X Roads, Hyderabad, India",
        "Ramanthapur, Hyderabad, India",
        "Nagole Metro Station, Hyderabad, India",
        "Habsiguda, Hyderabad, India",
        "Boduppal, Hyderabad, India",
        "Tarnaka, Hyderabad, India",
        "Ghatkesar, Telangana, India"
    ]

    results = []

    for place in locations:

        print("\nProcessing:", place)

        try:
            # Get geographical coordinates
            lat, lon = ox.geocode(place)

            # Distance from Uppal Stadium
            center_distance = calculate_distance(
                center_lat, center_lon, lat, lon
            )

            # Find nearest road network node
            nearest_node = ox.distance.nearest_nodes(
                G,
                X=lon,
                Y=lat
            )

            node_data = G.nodes[nearest_node]

            node_lat = node_data["y"]
            node_lon = node_data["x"]

            # Distance from location to nearest road node
            road_distance = calculate_distance(
                lat, lon, node_lat, node_lon
            )

            # Check coverage and road proximity
            if center_distance > SEARCH_RADIUS:
                status = "OUTSIDE 3 KM"

            elif road_distance > MAX_SNAP_DISTANCE:
                status = "ROAD TOO FAR"

            else:
                status = "MAPPED SUCCESSFULLY"

            results.append({
                "Location": place,
                "Latitude": lat,
                "Longitude": lon,
                "Distance_From_Stadium_m": round(center_distance, 2),
                "Nearest_Node": nearest_node,
                "Road_Distance_m": round(road_distance, 2),
                "Status": status
            })

            print("Distance from Stadium:", round(center_distance, 2), "m")
            print("Nearest Node:", nearest_node)
            print("Distance to Road:", round(road_distance, 2), "m")
            print("Status:", status)

        except Exception as e:
            print("Could not process location:", e)

        # Avoid sending geocoding requests too quickly
        time.sleep(1.2)

    # Save results
    if results:

        os.makedirs("outputs", exist_ok=True)

        df = pd.DataFrame(results)
        df.to_csv(OUTPUT_PATH, index=False)

        print("\n========== LOCATION MAPPING SUMMARY ==========")

        print(df[
            ["Location", "Distance_From_Stadium_m",
             "Road_Distance_m", "Status"]
        ].to_string(index=False))

        print("\nTotal Locations:", len(df))
        print(
            "Successfully Mapped:",
            (df["Status"] == "MAPPED SUCCESSFULLY").sum()
        )

        print("\nResults saved to:", OUTPUT_PATH)

    print("\nLOCATION MAPPING COMPLETED!")

if __name__ == "__main__":
    map_locations()
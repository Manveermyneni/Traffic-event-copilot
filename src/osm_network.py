import osmnx as ox
import networkx as nx
import os

def download_road_network():

    print("\n========== OSM ROAD NETWORK DOWNLOAD ==========")

    # Approximate coordinates of Uppal Stadium
    center_point = (17.4065, 78.5505)

    # Download roads within 3 km of the stadium
    distance = 3000

    print("\nDownloading Hyderabad road network...")
    print("Center: Uppal Stadium")
    print("Download Radius:", distance, "meters")

    # Download drivable road network using coordinates
    G = ox.graph_from_point(
        center_point,
        dist=distance,
        network_type="drive",
        simplify=True
    )

    print("\n========== ROAD NETWORK SUMMARY ==========")

    print("Total Junctions:", len(G.nodes))
    print("Total Road Segments:", len(G.edges))

    print("\nSample Junctions:")

    for node, data in list(G.nodes(data=True))[:5]:

        print(
            "Node:", node,
            "Latitude:", data.get("y"),
            "Longitude:", data.get("x")
        )

    print("\nSample Road Connections:")

    for u, v, data in list(G.edges(data=True))[:5]:

        print(
            "From:", u,
            "To:", v,
            "Length:", round(data.get("length", 0), 2),
            "meters",
            "One-way:", data.get("oneway", False)
        )

    # Save road network
    os.makedirs("data", exist_ok=True)

    output_path = "data/uppal_road_network.graphml"

    ox.save_graphml(G, filepath=output_path)

    print("\nRoad network saved successfully!")
    print("File:", output_path)

    return G


if __name__ == "__main__":

    road_graph = download_road_network()

    print("\nOSM ROAD NETWORK DOWNLOAD COMPLETED!")

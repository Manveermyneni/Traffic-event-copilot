import os
import pandas as pd
import osmnx as ox
import networkx as nx


# Project paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GRAPH_PATH = os.path.join(
    BASE_DIR, "data", "uppal_road_network.graphml"
)

LOCATION_PATH = os.path.join(
    BASE_DIR, "outputs", "location_mapping.csv"
)

OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")


def load_network_and_locations():

    print("\n========== ROUTE OPTIMIZATION ==========")

    # Load actual OSM road network
    G = ox.load_graphml(GRAPH_PATH)

    print("\nRoad network loaded successfully!")
    print("Total Nodes:", len(G.nodes))
    print("Total Edges:", len(G.edges))

    # Load mapped locations
    locations = pd.read_csv(LOCATION_PATH)

    locations = locations[
        locations["Status"] == "MAPPED SUCCESSFULLY"
    ].reset_index(drop=True)

    if locations.empty:
        raise ValueError("No successfully mapped locations found.")

    return G, locations


def display_locations(locations):

    print("\nAVAILABLE LOCATIONS")

    for index, row in locations.iterrows():
        print(f"{index + 1}. {row['Location']}")


def calculate_route(G, locations, source_index, destination_index):

    source = locations.iloc[source_index]
    destination = locations.iloc[destination_index]

    print("\n========== SELECTED LOCATIONS ==========")

    print("Source:", source["Location"])
    print("Destination:", destination["Location"])

    # Find nearest road nodes
    source_node = ox.distance.nearest_nodes(
        G,
        X=float(source["Longitude"]),
        Y=float(source["Latitude"])
    )

    destination_node = ox.distance.nearest_nodes(
        G,
        X=float(destination["Longitude"]),
        Y=float(destination["Latitude"])
    )

    print("\nNearest Road Nodes:")
    print("Source Node:", source_node)
    print("Destination Node:", destination_node)

    # Calculate shortest route based on road distance
    try:
        route = nx.shortest_path(
            G,
            source=source_node,
            target=destination_node,
            weight="length"
        )

        distance = nx.shortest_path_length(
            G,
            source=source_node,
            target=destination_node,
            weight="length"
        )

    except nx.NetworkXNoPath:
        print("\nNo valid road route exists between these locations.")
        return

    print("\n========== ROUTE RESULT ==========")

    print("Source:", source["Location"])
    print("Destination:", destination["Location"])
    print("Route Nodes:", len(route))
    print(f"Total Road Distance: {distance:.2f} meters")
    print(f"Total Road Distance: {distance / 1000:.2f} km")

    # Save route visualization
    output_path = os.path.join(
        OUTPUT_DIR, "optimized_route.png"
    )

    ox.plot_graph_route(
        G,
        route,
        route_color="red",
        route_linewidth=3,
        node_size=0,
        bgcolor="white",
        show=False,
        close=True,
        save=True,
        filepath=output_path,
        dpi=200
    )

    print("\nRoute visualization saved!")
    print("File:", output_path)

    print("\nROUTE OPTIMIZATION COMPLETED!")


def main():

    G, locations = load_network_and_locations()

    display_locations(locations)

    try:
        source_index = int(
            input("\nEnter source location number: ")
        ) - 1

        destination_index = int(
            input("Enter destination location number: ")
        ) - 1

        if not (0 <= source_index < len(locations)):
            raise ValueError("Invalid source location number.")

        if not (0 <= destination_index < len(locations)):
            raise ValueError("Invalid destination location number.")

        if source_index == destination_index:
            raise ValueError("Source and destination must be different.")

        calculate_route(
            G,
            locations,
            source_index,
            destination_index
        )

    except ValueError as error:
        print("\nInput Error:", error)


if __name__ == "__main__":
    main()
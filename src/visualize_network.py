import osmnx as ox
import os

def visualize_network():

    print("\n========== ROAD NETWORK VISUALIZATION ==========")

    # Load downloaded graph
    graph_path = "data/uppal_road_network.graphml"

    G = ox.load_graphml(graph_path)

    print("Graph loaded successfully!")
    print("Total Nodes:", len(G.nodes))
    print("Total Edges:", len(G.edges))

    # Create output directory
    os.makedirs("outputs", exist_ok=True)

    # Save road network visualization
    output_path = "outputs/uppal_road_network.png"

    fig, ax = ox.plot_graph(
        G,
        node_size=0,
        edge_linewidth=0.5,
        show=False,
        close=True,
        save=True,
        filepath=output_path,
        dpi=200
    )

    print("\nRoad network visualization saved!")
    print("Location:", output_path)

    print("\nNETWORK VISUALIZATION COMPLETED!")


if __name__ == "__main__":
    visualize_network()

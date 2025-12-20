import pickle
from classes.hetero_graph import HeteroGraph

# load the graph from the file
with open("data/semantic_memory/gym_01.pkl", "rb") as f:
    graph = pickle.load(f)

print(graph.conversations)


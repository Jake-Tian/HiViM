import pickle
from classes.hetero_graph import HeteroGraph

# load the graph from the file
with open("data/semantic_memory/gym_01.pkl", "rb") as f:
    graph = pickle.load(f)

degrees = graph.get_node_degrees()
print("Number of characters: ", len(graph.characters))
characters = [character for character in graph.characters if degrees[character] > 10]
print("Number of characters with degree greater than 10: ", len(characters))

for i in range(len(characters)-1):
    for j in range(i+1, len(characters)):
        print(f"Generating relationship between {characters[i]} and {characters[j]}")
        relationships = graph.character_relationships(characters[i], characters[j])
        print(relationships)


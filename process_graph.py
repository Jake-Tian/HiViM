import time
import pickle
from classes.hetero_graph import HeteroGraph

# load the graph from the file
with open("data/semantic_memory/gym_01.pkl", "rb") as f:
    graph = pickle.load(f)
    
search_results = graph.search_conversations("Which takeout should be taken to Anna?", 10)
messages = graph.get_conversation_messages_with_context(search_results)
print(len(messages[1]))
print(messages)
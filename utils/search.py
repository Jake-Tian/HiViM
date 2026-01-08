import json
import pickle
from pathlib import Path
from classes.hetero_graph import HeteroGraph
from utils.llm import generate_text_response
from utils.prompts import prompt_parse_query
from utils.general import strip_code_fences
from utils.edge_transfer import high_level_edges_to_string, low_level_edge_to_string


def load_graph(graph_path):
    """
    Load a HeteroGraph from a pickle file.
    
    Args:
        graph_path: Path to the graph pickle file
    
    Returns:
        HeteroGraph: The loaded graph object
    """
    graph_path = Path(graph_path)
    if not graph_path.exists():
        raise FileNotFoundError(f"Graph file not found: {graph_path}")
    
    with open(graph_path, "rb") as f:
        graph = pickle.load(f)
    
    return graph


def search(query, graph):
    """
    Search the graph for information relevant to a query and return a formatted string.
    
    This function:
    1. Parses the query using LLM
    2. Searches high-level edges, low-level edges, and conversations
    3. Formats all results into a single natural language string
    
    Args:
        query: Natural language query string
        graph: HeteroGraph instance to search
    
    Returns:
        str: Formatted string containing all search results in natural language
    """
    
    # Parse query using LLM
    try:
        strategy = generate_text_response(prompt_parse_query + "\n" + query)
    except Exception as e:
        raise Exception(f"Error generating query strategy: {e}")

    # Transfer the strategy into dictionary
    try:
        strategy_dict = json.loads(strip_code_fences(strategy))
    except json.JSONDecodeError as e:
        raise Exception(f"Error parsing strategy JSON: {e}\nRaw strategy response: {strategy}")

    # Extract strategy components with safe access
    triple = strategy_dict.get("query_triple")
    spatial_constraint = strategy_dict.get("spatial_constraint")
    speaker_strict = strategy_dict.get("speaker_strict")
    allocation = strategy_dict.get("allocation", {})

    if not triple:
        raise ValueError("query_triple not found in strategy")

    # Get k values from allocation, with defaults as fallback
    k_high_level = allocation.get("k_high_level", 10)
    k_low_level = allocation.get("k_low_level", 10)
    k_conversations = allocation.get("k_conversations", 10)

    # Search the graph
    try:
        # Search high-level edges
        high_level_edges = graph.search_high_level_edges(triple, k_high_level)
        
        # Search low-level edges
        low_level_edges = graph.search_low_level_edges(
            triple, 
            k_low_level,
            spatial_constraint
        )
        
        # Search conversations (use original query string)
        conversation_results = graph.search_conversations(
            query,
            k_conversations,
            speaker_strict
        )
        
    except Exception as e:
        raise Exception(f"Error searching graph: {e}")

    # Format results into strings
    result_sections = []
    
    # Format high-level edges
    if high_level_edges:
        high_level_str = high_level_edges_to_string(high_level_edges)
        if high_level_str:
            result_sections.append("**High-Level Information (Character Attributes and Relationships): **\n")
            result_sections.append(high_level_str)
            result_sections.append("")
    
    # Format low-level edges
    if low_level_edges:
        low_level_str = low_level_edge_to_string(low_level_edges)
        if low_level_str:
            result_sections.append("**Low-Level Information (Actions and Events): **\n")
            result_sections.append(low_level_str)
            result_sections.append("")
    
    # Format conversations
    if conversation_results:
        conversation_str = graph.get_conversation_messages_with_context(conversation_results)
        if conversation_str:
            result_sections.append("**Conversations: **\n")
            result_sections.append(conversation_str)
    
    # Combine all sections
    final_result = "\n".join(result_sections)
    
    # If no results found, return a message
    if not final_result.strip():
        return "No relevant information found for this query."
    
    return final_result


if __name__ == "__main__":
    # Example usage
    with open("data/semantic_memory/gym_01.pkl", "rb") as f:
        graph = pickle.load(f)
    query = "Which takeout should be taken to Anna?"
    
    try:
        result = search(query, graph)
        print(result)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
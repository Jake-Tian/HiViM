import pickle
from utils.search import search
from utils.llm import generate_text_response
from utils.prompts import prompt_semantic_video


def reason(question, graph):
    
    # Search the graph for relevant information
    try:
        search_results = search(question, graph)
    except Exception as e:
        raise Exception(f"Error searching graph: {e}")
    
    # Combine prompt, question, and search results
    prompt = prompt_semantic_video + "\n\nExtracted knowledge from graph:\n" + search_results + "\n\nQuestion: " + question
    
    # Get semantic answer from LLM
    try:
        response = generate_text_response(prompt)
        return response.strip()
    except Exception as e:
        raise Exception(f"Error generating semantic answer: {e}")


if __name__ == "__main__":
    # Example usage
    with open("data/semantic_memory/gym_01.pkl", "rb") as f:
        graph = pickle.load(f)
    
    question = "Which takeout should be taken to Anna?"
    
    try:
        result = reason(question, graph)
        print(result)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

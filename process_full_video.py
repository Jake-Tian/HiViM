import glob
import json
import pickle
from pathlib import Path
from classes.hetero_graph import HeteroGraph
from utils.llm import generate_text_response
from utils.mllm_pictures import generate_messages, get_response
from utils.prompts import prompt_generate_episodic_memory, prompt_extract_triples
from utils.general import strip_code_fences, load_video_list


def process_full_video(frames_dir, output_graph_path=None, output_episodic_memory_path=None):
    """
    Process video frames to build episodic and semantic memory.
    
    Args:
        frames_dir: Path to directory containing frame folders (e.g., "data/frames/gym_01")
        output_graph_path: Path to save the graph pickle file (default: "data/semantic_memory/{video_name}.pkl")
        output_episodic_memory_path: Path to save episodic memory JSON (default: "data/episodic_memory/{video_name}.json")
    
    Returns:
        tuple: (graph, episodic_memory) - The processed graph and episodic memory dictionary
    """
    frames_dir = Path(frames_dir)
    video_name = frames_dir.name
    
    # Set default output paths if not provided
    if output_graph_path is None:
        output_graph_path = f"data/semantic_memory/{video_name}.pkl"
    if output_episodic_memory_path is None:
        output_episodic_memory_path = f"data/episodic_memory/{video_name}.json"
    
    # Get sorted image folders
    image_folders = sorted(
        [str(folder) for folder in frames_dir.iterdir() if folder.is_dir()],
        key=lambda x: int(Path(x).name)
    )
    
    character_appearance = "{}"
    previous_conversation = False
    episodic_memory = dict()
    graph = HeteroGraph()
    
    for folder in image_folders:
        print("--------------------------------")
        print("Processing folder: ", folder)
        clip_id = int(folder.split("/")[-1])
        response_dict = dict()
        # Collect images in the current folder
        current_images = sorted(
            glob.glob(f"{folder}/*.jpg"),
            key=lambda p: int(Path(p).stem) if Path(p).stem.isdigit() else p,
        )

        #--------------------------------
        # Episodic Memory
        #--------------------------------
        prompt = "Character appearance from previous videos: \n" + character_appearance + "\n" + prompt_generate_episodic_memory
        messages = generate_messages(current_images, prompt)
        response = get_response(messages)
        print(response)
        response = strip_code_fences(response)
        response_dict = json.loads(response)


        # 1. Process the character's behavior
        behaviors = response_dict["characters_behavior"]
        if behaviors and len(behaviors) > 0 and behaviors[0].startswith("Equivalance:"):
            equivalence = behaviors[0].split(":")[1].split(",")
            behaviors = behaviors[1:]
            graph.rename_character(equivalence[0].strip(), equivalence[1].strip())

        # 2. Process the character appearance
        character_appearance = response_dict["character_appearance"]
        for character in character_appearance:
            if character not in graph.characters:
                graph.add_character(character)

        # 3. Process the conversation
        conversation = response_dict["conversation"]

        if len(conversation) > 0:
            graph.update_conversation(clip_id, conversation, previous_conversation=previous_conversation)
            previous_conversation = True  # Set to True for next iteration
        else:
            previous_conversation = False  # No conversation in this clip, reset for next iteration

        scene = response_dict["scene"]

        #--------------------------------
        # Semantic Memory
        #--------------------------------
        behavior_prompt = prompt_extract_triples + "\n" + "\n".join(behaviors)
        triples_response = generate_text_response(behavior_prompt)

        triples_response = strip_code_fences(triples_response)
        triples = json.loads(triples_response)
        graph.insert_triples(triples, clip_id, scene)
        print(f"Inserted {len(triples)} triples into graph for clip {clip_id}")

        character_appearance = json.dumps(character_appearance)

        # Store episodic memory for this clip
        episodic_memory[clip_id] = {
            "folder": folder,
            "characters_behavior": behaviors,
            "conversation": conversation,
            "character_appearance": character_appearance,
            "scene": scene,
            "triples": triples
        }

    # Save the graph to a file
    output_graph_path = Path(output_graph_path)
    output_graph_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_graph_path, "wb") as f:
        pickle.dump(graph, f)

    # Save the episodic memory to a JSON file
    output_episodic_memory_path = Path(output_episodic_memory_path)
    output_episodic_memory_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_episodic_memory_path, "w") as f:
        json.dump(episodic_memory, f, indent=2)
    print(f"\n✓ Saved episodic memory for {len(episodic_memory)} clips to {output_episodic_memory_path}")
    
    return graph, episodic_memory


def main():
    """Main function to process video frames."""
    import sys
    
    video_names = load_video_list()
    
    # Parse range from command line (e.g., "1-20" or "21-40")
    if len(sys.argv) > 1:
        start, end = map(int, sys.argv[1].split('-'))
        selected = video_names[start-1:end]
    else:
        selected = video_names
    
    for video_name in selected:
        frames_dir = Path(f"data/frames/{video_name}")
        if not frames_dir.exists():
            print(f"Skipping {video_name}: frames not found")
            continue
        print(f"\nProcessing {video_name}...")
        graph, episodic_memory = process_full_video(frames_dir)
        print(f"✓ {video_name} complete. Graph has {len(graph.characters)} characters and {len(graph.edges)} edges.")


if __name__ == "__main__":
    main()


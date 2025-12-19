import json
from .node_class import CharacterNode, ObjectNode
from .edge_class import Edge
from .conversation import Conversation
from collections import defaultdict
from utils.prompts import prompt_character_summary, prompt_character_relationships
from utils.llm import generate_text_response
from utils.general import strip_code_fences


class HeteroGraph:
    def __init__(self):

        self.characters = {}   # name → CharacterNode object
        self.objects = {}   # (name, owner, attribute) → ObjectNode object (tuple key)
        self.conversations = {}   # id → Conversation object
        self.edges = {}   # id → Edge object
        self.current_conversation_id = None  # Track the most recent conversation ID

        # adjacency lists for O(1) search
        self.adjacency_list_out = defaultdict(list)  # node → list of edge IDs (outgoing edges)
        self.adjacency_list_in = defaultdict(list)   # node → list of edge IDs (incoming edges)

        robot = CharacterNode("<robot>")
        self.characters[robot.name] = robot


    # --------------------------------------------------------
    # Node API
    # --------------------------------------------------------
    def add_character(self, name):
        """Add a new character."""
        character = CharacterNode(name)
        self.characters[character.name] = character
        return character.name
    
    def get_character(self, name):
        """Get a character by name. Returns None if not found."""
        return self.characters.get(name)
    
    def rename_character(self, old_name, new_name):
        """
        Rename a character and update all references throughout the graph.
        
        This function:
        1. Updates the character's name in self.characters
        2. Updates all object nodes whose ownership references this character
        3. Updates all edges where this character appears as source or target
        4. Updates adjacency lists accordingly
        
        Args:
            old_name: Current character name in format <character_X> (e.g., "<character_1>")
            new_name: New character name as plain text without angle brackets (e.g., "Alice")
                     Will be stored in graph as "<Alice>"
        
        Returns:
            bool: True if rename was successful, False if old_name not found or new_name already exists
        """
        # Ensure old_name has angle brackets and matches <character_X> format
        if not old_name.startswith("<") or not old_name.endswith(">"):
            old_name = f"<{old_name}>"
        
        # Validate old_name is in <character_X> format
        if not old_name.startswith("<character_") or not old_name.endswith(">"):
            # Allow it but warn - the user should pass <character_X> format
            pass
        
        # Remove angle brackets from new_name if present, then add them for storage
        new_name_plain = new_name.strip("<>")
        new_name_stored = f"<{new_name_plain}>"
        
        # Check if old character exists
        if old_name not in self.characters:
            return False
        
        # Check if new name already exists (and it's not the same character)
        if new_name_stored in self.characters and new_name_stored != old_name:
            return False
        
        # Get the character node
        character = self.characters[old_name]
        
        # 1. Update character's name property
        character.name = new_name_stored
        
        # 2. Move character in self.characters dictionary
        del self.characters[old_name]
        self.characters[new_name_stored] = character
        
        # 3. Update object nodes that have this character as owner
        objects_to_update = []
        for obj_key, obj_node in list(self.objects.items()):
            name, owner, attribute = obj_key
            if owner == old_name:
                # Create new key with updated owner
                new_key = (name, new_name_stored, attribute)
                objects_to_update.append((obj_key, new_key, obj_node))
        
        # Update object dictionary keys
        for old_key, new_key, obj_node in objects_to_update:
            del self.objects[old_key]
            self.objects[new_key] = obj_node
            # Update the node's owner attribute
            obj_node.owner = new_name_stored
        
        # 4. Update edges where this character appears as source or target
        # Collect all edges connected to this character
        all_edge_ids = set(self.adjacency_list_out.get(old_name, [])) | set(self.adjacency_list_in.get(old_name, []))
        
        for edge_id in all_edge_ids:
            edge = self.edges.get(edge_id)
            if edge is None:
                continue
            
            # Update source if it matches old_name
            if edge.source == old_name:
                edge.source = new_name_stored
            # Update target if it matches old_name
            if edge.target == old_name:
                edge.target = new_name_stored
        
        # 5. Update adjacency lists
        # Move edge IDs from old_name to new_name_stored in both adjacency lists
        if old_name in self.adjacency_list_out:
            edge_ids_out = self.adjacency_list_out.pop(old_name)
            self.adjacency_list_out[new_name_stored] = edge_ids_out
        
        if old_name in self.adjacency_list_in:
            edge_ids_in = self.adjacency_list_in.pop(old_name)
            self.adjacency_list_in[new_name_stored] = edge_ids_in
        
        return True
    
    def get_neighbors(self, name):
        """
        Get all neighbors of a node (both incoming and outgoing).
        """
        result = set()
        
        # Check outgoing edges (where node is source)
        for eid in self.adjacency_list_out[name]:
            e = self.edges[eid]
            result.add(e.target)
        
        # Check incoming edges (where node is target)
        for eid in self.adjacency_list_in[name]:
            e = self.edges[eid]
            result.add(e.source)
        
        return result
    
    def get_node_degrees(self):
        """
        Calculate the degree (number of connected edges) for each node in the graph.
        """
        degrees = {}
        
        # Get all nodes that appear in either adjacency list
        all_nodes = set(self.adjacency_list_out.keys()) | set(self.adjacency_list_in.keys())
        
        # Calculate degree for each node (outgoing + incoming)
        for node in all_nodes:
            out_degree = len(self.adjacency_list_out[node])
            in_degree = len(self.adjacency_list_in[node])
            degrees[node] = out_degree + in_degree
        
        return degrees

    def _parse_node_string(self, node_str):
        """
        Parse a node string to determine if it's a character or object, and extract owner/attribute.
        """
        if node_str is None:
            return (False, None, None, None)
        
        node_str = str(node_str).strip()
        
        # Check if it's a character node (surrounded by angle brackets)
        if node_str.startswith("<") and node_str.endswith(">"):
            # Keep the angle brackets for consistency with storage
            character_name = node_str  # Keep angle brackets
            return (True, character_name, None, None)
        
        # It's an object node - parse owner and attribute
        # Format can be: "object", "object@owner", "object#attribute", "object@owner#attribute", "object#attribute@owner"
        owner = None
        attribute = None
        name = node_str
        
        # Handle different formats
        # Priority: @ comes before # in parsing (owner is more specific)
        if "@" in node_str and "#" in node_str:
            # Both @ and # exist - determine order
            at_pos = node_str.find("@")
            hash_pos = node_str.find("#")
            
            if at_pos < hash_pos:
                # Format: "object@owner#attribute"
                parts = node_str.split("@", 1)
                name = parts[0]
                rest = parts[1]
                if "#" in rest:
                    owner_part, attribute = rest.split("#", 1)
                    owner = owner_part
                else:
                    owner = rest
            else:
                # Format: "object#attribute@owner"
                parts = node_str.split("#", 1)
                name = parts[0]
                rest = parts[1]
                if "@" in rest:
                    attribute_part, owner = rest.split("@", 1)
                    attribute = attribute_part
                else:
                    attribute = rest
        elif "@" in node_str:
            # Only @ exists: "object@owner"
            parts = node_str.split("@", 1)
            name = parts[0]
            owner = parts[1]
        elif "#" in node_str:
            # Only # exists: "object#attribute"
            parts = node_str.split("#", 1)
            name = parts[0]
            attribute = parts[1]
        
        # Keep owner as-is: if it has angle brackets, it's a character reference; otherwise it's not
        
        return (False, name, owner, attribute)
    
    def _object_key_to_string(self, key):
        """
        Convert tuple key to string representation for edges.
        """
        name, owner, attribute = key
        # Owner should already have angle brackets if it's a character reference (from parsing)
        if owner and attribute:
            return f"{name}@{owner}#{attribute}"
        elif owner:
            return f"{name}@{owner}"
        elif attribute:
            return f"{name}#{attribute}"
        else:
            return name
    
    def _string_to_object_key(self, node_str):
        """
        Parse a node string and return tuple key for object nodes.
        """
        is_char, name, owner, attribute = self._parse_node_string(node_str)
        if is_char:
            return None  # Characters don't use tuple keys
        return (name, owner, attribute)
    
    def _get_object_node_by_key(self, key):
        """
        Get an object node by tuple key.
        """
        return self.objects.get(key)
    
    def get_object_node(self, node_str):
        """
        Get an object node by its string representation.
        For character nodes, returns None (use get_character instead).
        """
        obj_key = self._string_to_object_key(node_str)
        if obj_key is None:
            return None  # It's a character node
        return self.objects.get(obj_key)
    
    def _get_or_create_object_node(self, name, owner=None, attribute=None):
        """
        Get an existing object node or create a new one.
        Uniqueness is determined by name + owner + attribute combination (tuple key).
        """
        # Create tuple key for uniqueness
        tuple_key = (name, owner, attribute)
        
        # Check if object already exists
        if tuple_key in self.objects:
            string_repr = self._object_key_to_string(tuple_key)
            return (tuple_key, string_repr)
        
        # Create new object node
        obj_node = ObjectNode(name, owner=owner, attribute=attribute)
        self.objects[tuple_key] = obj_node
        
        # Return both tuple key and string representation
        string_repr = self._object_key_to_string(tuple_key)
        return (tuple_key, string_repr)
    
    def insert_triples(self, triples, clip_id, scene):
        """
        Insert triples into the graph.
        
        Args:
            triples: List of triples, each triple is [source, edge_content, target]
            clip_id: ID of the clip these triples belong to
        
        Rules:
        1. Each triple: [source, edge_content, target]
        2. Elements with angle brackets <> are character nodes, otherwise object nodes
        3. Object nodes can have @owner and/or #attribute suffixes
        4. Character nodes should already exist; object nodes are created if needed
        5. Uniqueness of object nodes is determined by name + owner + attribute
        6. Don't insert duplicate edges in the same list
        """
        if not triples:
            return
        
        # Track inserted edges to avoid duplicates within the same list
        # Use (source, target, content) as the key
        seen_edges = set()
        
        for triple in triples:
            if not isinstance(triple, list) or len(triple) < 3:
                continue
            
            source_str = triple[0]
            edge_content = triple[1]
            target_str = triple[2]
            
            # Skip if source is None
            if source_str is None:
                continue
            
            # Skip if edge content is None/null or empty
            if edge_content is None or (isinstance(edge_content, str) and not edge_content.strip()):
                continue
            
            # Parse source node
            is_char_src, src_name, src_owner, src_attr = self._parse_node_string(source_str)
            
            if is_char_src:
                # Source is a character - verify it exists (characters are stored with angle brackets)
                # src_name already has angle brackets from _parse_node_string
                if src_name not in self.characters:
                    print(f"Warning: Character node '{src_name}' not found in graph, skipping triple: {triple}")
                    continue
                source_node_name = src_name
            else:
                # Source is an object - get or create (returns tuple_key, string_repr)
                _, source_node_name = self._get_or_create_object_node(src_name, owner=src_owner, attribute=src_attr)
            
            # Handle null/Null target - use None as target but don't create object node
            if target_str is None or (isinstance(target_str, str) and target_str.lower() == "null"):
                target_node_name = None
            else:
                # Parse target node
                is_char_tgt, tgt_name, tgt_owner, tgt_attr = self._parse_node_string(target_str)
                
                if is_char_tgt:
                    # Target is a character - verify it exists (characters are stored with angle brackets)
                    # tgt_name already has angle brackets from _parse_node_string
                    if tgt_name not in self.characters:
                        print(f"Warning: Character node '{tgt_name}' not found in graph, skipping triple: {triple}")
                        continue
                    target_node_name = tgt_name
                else:
                    # Target is an object - get or create (returns tuple_key, string_repr)
                    _, target_node_name = self._get_or_create_object_node(tgt_name, owner=tgt_owner, attribute=tgt_attr)
            
            # Check for duplicate edge
            edge_key = (source_node_name, target_node_name, edge_content)
            if edge_key in seen_edges:
                continue  # Skip duplicate
            
            seen_edges.add(edge_key)
            
            # Create and add edge
            edge = Edge(clip_id=clip_id, source=source_node_name, target=target_node_name, content=edge_content, scene=scene)
            self.add_edge(edge)
    

    # --------------------------------------------------------
    # Conversation API
    # --------------------------------------------------------
    def update_conversation(self, clip_id, messages, previous_conversation=False):
        """
        Update or create a conversation in the graph.
        
        Args:
            clip_id: ID of the current clip
            messages: List of [speaker, text] pairs for the conversation
            previous_conversation: If True, update the current conversation; if False, create a new one
        
        Returns:
            int: Conversation ID
        """
        if not messages:
            return None
        
        if previous_conversation and self.current_conversation_id is not None:
            # Update existing conversation
            conversation = self.conversations.get(self.current_conversation_id)
            if conversation:
                conversation.add_messages(messages)
                conversation.add_clip(clip_id)
                return conversation.id
            else:
                # Current conversation ID is invalid, create new one
                previous_conversation = False
        
        if not previous_conversation:
            # Create new conversation
            conversation = Conversation(clip_id=clip_id, messages=messages)
            self.conversations[conversation.id] = conversation
            self.current_conversation_id = conversation.id
            return conversation.id


    # --------------------------------------------------------
    # Edge API
    # --------------------------------------------------------
    def add_edge(self, edge):
        # Check if source and target nodes exist
        # Edges store node names as strings, so we need to check:
        # - For characters: direct lookup in self.characters (with angle brackets)
        # - For objects: parse the string and check tuple key in self.objects
        
        source_exists = False
        # If source has angle brackets, it's a character; otherwise it's an object
        if edge.source.startswith("<") and edge.source.endswith(">"):
            # It's a character - check directly
            if edge.source in self.characters:
                source_exists = True
        else:
            # It's an object - parse and check tuple key
            obj_key = self._string_to_object_key(edge.source)
            if obj_key is not None and obj_key in self.objects:
                source_exists = True
        
        target_exists = False
        # Special case: None is allowed as target without creating a node
        if edge.target is None:
            target_exists = True
        # If target has angle brackets, it's a character; otherwise it's an object
        elif edge.target.startswith("<") and edge.target.endswith(">"):
            # It's a character - check directly
            if edge.target in self.characters:
                target_exists = True
        else:
            # It's an object - parse and check tuple key
            obj_key = self._string_to_object_key(edge.target)
            if obj_key is not None and obj_key in self.objects:
                target_exists = True
        
        if not source_exists:
            raise ValueError(f"Source node '{edge.source}' not found in graph")
        if not target_exists:
            raise ValueError(f"Target node '{edge.target}' not found in graph")

        self.edges[edge.id] = edge
        # Add to both adjacency lists (edges are directed by default)
        self.adjacency_list_out[edge.source].append(edge.id)
        # Handle None target for adjacency list
        if edge.target is not None:
            self.adjacency_list_in[edge.target].append(edge.id)
        else:
            self.adjacency_list_in[None].append(edge.id)

        return edge.id

    def get_edge(self, edge_id):
        return self.edges.get(edge_id)

    def edges_from(self, node_id):
        return set(self.adjacency_list_out[node_id])

    def edges_to(self, node_id):
        return set(self.adjacency_list_in[node_id])

    def edges_of(self, node_id):
        return set(self.adjacency_list_out[node_id]) | set(self.adjacency_list_in[node_id])

    def get_connected_edges(self, character1, character2):
        """
        Get all edges directly or indirectly connected between two characters.
        
        Direct connection: An edge where one character is source and the other is target (or vice versa).
        Indirect connection: character1 connects to an object, and that object connects to character2,
        where the clip_id difference between the two edges is less than 4.
        Ownership connection: character1 interacts with an object that belongs to character2 (or vice versa).
        
        Args:
            character1: First character name (with or without angle brackets, e.g., "<Alice>" or "Alice")
            character2: Second character name (with or without angle brackets, e.g., "<Bob>" or "Bob")
        
        Returns:
            list: List of Edge objects that are directly or indirectly connected between the two characters
        """
        # Normalize character names (add angle brackets if needed)
        if not character1.startswith("<") or not character1.endswith(">"):
            character1 = f"<{character1}>"
        if not character2.startswith("<") or not character2.endswith(">"):
            character2 = f"<{character2}>"
        
        # Check if both characters exist
        if character1 not in self.characters:
            raise ValueError(f"Character '{character1}' not found in graph")
        if character2 not in self.characters:
            raise ValueError(f"Character '{character2}' not found in graph")
        
        result_edges = []
        result_edge_ids = set()
        
        # 1. Get all direct edges (where either character is source or target)
        char1_edges = self.edges_of(character1)
        char2_edges = self.edges_of(character2)
        
        # Direct edges: edges where both characters are involved
        direct_edges = char1_edges & char2_edges
        for edge_id in direct_edges:
            if edge_id not in result_edge_ids:
                edge = self.edges.get(edge_id)
                if edge is not None:
                    result_edges.append(edge)
                    result_edge_ids.add(edge_id)
        
        # 2. Find indirect connections through objects
        # Get all edges where character1 is involved
        for edge_id in char1_edges:
            edge1 = self.edges.get(edge_id)
            if edge1 is None:
                continue
            
            # Get the other node (not character1)
            other_node = None
            if edge1.source == character1:
                other_node = edge1.target
            elif edge1.target == character1:
                other_node = edge1.source
            
            # Skip if other_node is None or is a character
            if other_node is None:
                continue
            
            # Check if other_node is an object (not a character)
            is_char, _, _, _ = self._parse_node_string(other_node)
            if is_char:
                continue  # Skip if it's a character
            
            # Find all edges where this object connects to character2
            object_edges = self.edges_of(other_node)
            for edge_id2 in object_edges:
                edge2 = self.edges.get(edge_id2)
                if edge2 is None:
                    continue
                
                # Check if edge2 connects the object to character2
                connects_to_char2 = False
                if (edge2.source == other_node and edge2.target == character2) or \
                   (edge2.target == other_node and edge2.source == character2):
                    connects_to_char2 = True
                
                if connects_to_char2:
                    # Check clip_id difference < 4
                    clip_diff = abs(edge1.clip_id - edge2.clip_id)
                    if clip_diff < 4:
                        # Add both edges to result
                        if edge_id not in result_edge_ids:
                            result_edges.append(edge1)
                            result_edge_ids.add(edge_id)
                        if edge_id2 not in result_edge_ids:
                            result_edges.append(edge2)
                            result_edge_ids.add(edge_id2)
        
        # 3. Find ownership connections: character1 interacts with object owned by character2
        for edge_id in char1_edges:
            edge = self.edges.get(edge_id)
            if edge is None:
                continue
            
            # Get the other node (not character1)
            other_node = None
            if edge.source == character1:
                other_node = edge.target
            elif edge.target == character1:
                other_node = edge.source
            
            # Skip if other_node is None or is a character
            if other_node is None:
                continue
            
            # Check if other_node is an object (not a character)
            is_char, _, _, _ = self._parse_node_string(other_node)
            if is_char:
                continue  # Skip if it's a character
            
            # Get the object node to check ownership
            obj_key = self._string_to_object_key(other_node)
            if obj_key is not None:
                obj_node = self.objects.get(obj_key)
                if obj_node is not None and obj_node.owner == character2:
                    # Character1 interacts with an object owned by character2
                    if edge_id not in result_edge_ids:
                        result_edges.append(edge)
                        result_edge_ids.add(edge_id)
        
        # 4. Find ownership connections: character2 interacts with object owned by character1
        for edge_id in char2_edges:
            edge = self.edges.get(edge_id)
            if edge is None:
                continue
            
            # Get the other node (not character2)
            other_node = None
            if edge.source == character2:
                other_node = edge.target
            elif edge.target == character2:
                other_node = edge.source
            
            # Skip if other_node is None or is a character
            if other_node is None:
                continue
            
            # Check if other_node is an object (not a character)
            is_char, _, _, _ = self._parse_node_string(other_node)
            if is_char:
                continue  # Skip if it's a character
            
            # Get the object node to check ownership
            obj_key = self._string_to_object_key(other_node)
            if obj_key is not None:
                obj_node = self.objects.get(obj_key)
                if obj_node is not None and obj_node.owner == character1:
                    # Character2 interacts with an object owned by character1
                    if edge_id not in result_edge_ids:
                        result_edges.append(edge)
                        result_edge_ids.add(edge_id)
        
        return result_edges


    # --------------------------------------------------------
    # Abstract Information API
    # --------------------------------------------------------
    def character_attributes(self, character_name):
        """
        Extract character attributes by analyzing all edges connected to the character.
        
        This function:
        1. Collects all edges (incoming and outgoing) connected to the character
        2. Formats them as a readable string (one edge per line)
        3. Combines with prompt_character_summary
        4. Uses LLM to generate character attributes
        5. Parses the LLM output and creates attribute edges in the graph
        
        Args:
            character_name: Character name (with or without angle brackets, e.g., "<Alice>" or "Alice")
        
        Returns:
            dict: Dictionary of attributes with confidence scores
        """
        # Ensure character name has angle brackets for lookup
        if not character_name.startswith("<") or not character_name.endswith(">"):
            character_name = f"<{character_name}>"
        
        # Check if character exists
        if character_name not in self.characters:
            raise ValueError(f"Character '{character_name}' not found in graph")
        
        # Get all edges connected to this character
        edge_ids = self.edges_of(character_name)
        
        if not edge_ids:
            # No edges found, return empty dictionary
            return {}
        
        # Format edges as strings (one per line)
        edge_lines = []
        for edge_id in sorted(edge_ids):  # Sort for consistent ordering
            edge = self.edges.get(edge_id)
            if edge is None:
                continue
            
            # Format: source, content, target
            target_str = edge.target if edge.target is not None else "null"
            edge_str = f"{edge.source}, {edge.content}, {target_str}"
            if edge.scene:
                edge_str += f", scene: {edge.scene}"
            
            edge_lines.append(edge_str)
        
        # Combine all edge descriptions into a single string
        edges_text = "\n".join(edge_lines)
        
        # Create the full prompt with proper string formatting
        full_prompt = f"Character: {character_name}\n\nCharacter behaviors (from graph edges):\n{edges_text}\n{prompt_character_summary}"
        try:
            attributes_response = generate_text_response(full_prompt)
        except Exception as e:
            print(f"LLM call failed, retrying... Error: {e}")
            attributes_response = generate_text_response(full_prompt)
        
        # Parse the LLM response
        attributes_response = strip_code_fences(attributes_response)
        try:
            attributes_dict = json.loads(attributes_response)
        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM response as JSON: {e}")
            print(f"Response was: {attributes_response}")
            return {}
        
        # Create edges for each attribute
        for attribute_name, confidence in attributes_dict.items():
            # Only create edge if confidence >= 50 (as per prompt instructions)
            if not isinstance(confidence, (int, float)) or confidence < 50:
                continue
                
            edge = Edge(
                clip_id=0,
                source=character_name,
                target=None,
                content=attribute_name,
                scene=None,
                confidence=confidence
            )
            try:
                self.add_edge(edge)
            except Exception as e:
                pass
        
        return attributes_dict

    def character_relationships(self, character1, character2):
        """
        Extract character relationships by analyzing all edges between two characters.
        
        This function:
        1. Gets all edges directly or indirectly connected between the two characters
        2. Formats them as a readable string (one edge per line)
        3. Combines with prompt_character_relationships
        4. Uses LLM to generate relationship descriptions
        5. Parses the LLM output and creates relationship edges in the graph
        
        Args:
            character1: First character name (with or without angle brackets, e.g., "<Alice>" or "Alice")
            character2: Second character name (with or without angle brackets, e.g., "<Bob>" or "Bob")
        
        Returns:
            list: List of relationship tuples [character1, relationship, character2, confidence]
        """
        # Normalize character names (add angle brackets if needed)
        if not character1.startswith("<") or not character1.endswith(">"):
            character1 = f"<{character1}>"
        if not character2.startswith("<") or not character2.endswith(">"):
            character2 = f"<{character2}>"
        
        # Check if both characters exist
        if character1 not in self.characters:
            raise ValueError(f"Character '{character1}' not found in graph")
        if character2 not in self.characters:
            raise ValueError(f"Character '{character2}' not found in graph")
        
        # Get all connected edges between the two characters
        connected_edges = self.get_connected_edges(character1, character2)
        
        if not connected_edges or len(connected_edges) < 3:
            return []
        
        # Format edges as strings (one per line)
        edge_lines = []
        for edge in sorted(connected_edges, key=lambda e: (e.clip_id, e.id)):  # Sort by clip_id for chronological order
            # Format: source, content, target
            target_str = edge.target if edge.target is not None else "null"
            edge_str = f"{edge.source}, {edge.content}, {target_str}"
            if edge.scene:
                edge_str += f", scene: {edge.scene}"
            
            edge_lines.append(edge_str)
        
        # Combine all edge descriptions into a single string
        edges_text = "\n".join(edge_lines)
        
        # Create the full prompt with proper string formatting
        full_prompt = f"Character 1: {character1}\nCharacter 2: {character2}\n\nCharacter interactions (from graph edges):\n{edges_text}\n{prompt_character_relationships}"
        try:
            relationships_response = generate_text_response(full_prompt)
        except Exception as e:
            print(f"LLM call failed, retrying... Error: {e}")
            relationships_response = generate_text_response(full_prompt)
        
        # Parse the LLM response
        relationships_response = strip_code_fences(relationships_response)
        try:
            relationships_list = json.loads(relationships_response)
        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM response as JSON: {e}")
            print(f"Response was: {relationships_response}")
            return []
        
        # Validate and create edges for each relationship
        relationships_created = []
        for rel in relationships_list:
            # Expected format: [character1, relationship, character2, confidence]
            if not isinstance(rel, list) or len(rel) < 4:
                continue
            
            rel_char1, relationship, rel_char2, confidence = rel[0], rel[1], rel[2], rel[3]
            
            # Only create edge if confidence >= 50 (as per prompt instructions)
            if not isinstance(confidence, (int, float)) or confidence < 50:
                continue
            
            # Normalize character names in the relationship
            if not rel_char1.startswith("<") or not rel_char1.endswith(">"):
                rel_char1 = f"<{rel_char1}>"
            if not rel_char2.startswith("<") or not rel_char2.endswith(">"):
                rel_char2 = f"<{rel_char2}>"
            
            # Verify the characters match the input (order might be swapped)
            if (rel_char1 == character1 and rel_char2 == character2) or \
               (rel_char1 == character2 and rel_char2 == character1):
                # Create edge: source=character1, content=relationship, target=character2
                # Use the order from the relationship (LLM's choice)
                edge = Edge(
                    clip_id=0,
                    source=rel_char1,
                    target=rel_char2,
                    content=relationship,
                    scene=None,
                    confidence=confidence
                )
                try:
                    self.add_edge(edge)
                    relationships_created.append(rel)
                except Exception as e:
                    print(f"Failed to add relationship edge: {e}")
                    pass
        
        return relationships_created


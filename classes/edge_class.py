from utils.llm import get_embedding

class Edge:
    """Edge between two nodes, supports integer IDs."""
    _id_counter = 0

    @classmethod
    def next_id(cls):
        cls._id_counter += 1
        return cls._id_counter

    def __init__(self, clip_id, source, target, content, scene, embedding=None, confidence=None):
        self.id = Edge.next_id()
        self.clip_id = clip_id
        self.source = source  
        self.target = target 
        self.content = content
        self.scene = scene
        self.confidence = confidence
        self.embedding = embedding

    def __repr__(self):
        return f"Edge({self.source} -> {self.target}, content={self.content})"

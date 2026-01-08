
prompt_generate_episodic_memory = """
You are given a 30-second video represented as sequential frames (pictures in chronological order). 

Your tasks: 

1. **Characters' Behavior**
   - Describe each character's behavior in chronological order.
   - Include:
     (a) Interaction with objects in the scene.
     (b) Interaction with other characters.
     (c) Actions and movements.
   - Each entry must describe exactly one event/detail. Split sentences if needed.
   - Output format: Python list of strings.

2. **Conversation**
   - Record the dialogue based on subtitles.
   - Always use characters' real name existed in the subtitle. 
   - Output format: List of two-element lists [character, content].

3. **Character Appearance**
   - Describe each character's appearance: facial features, clothing, body shape, hairstyle, or other distinctive characteristics.
   - Each characteristic should be concise, separated by commas.
   - **New characters**: Before creating a new unknown character (<character_X>), FIRST check if any previously seen unknown character from earlier clips matches the appearance. If a match is found, add an equivalence line at the **start of characters_behavior**. Then remove its information from character_appearance. Only create a new unknown character if no previous unknown character matches.
   - **Existing characters** (if previous appearance info provided): Update if changes observed, enhance if new details visible, otherwise keep unchanged.
   - If the character leaves the scene, keep their appearance information in the dictionary.
   - If two characters in the scene look similar, extract the most distinctive features to describe them.
   - **Minimize unknown characters**: Try to match new characters with previously seen unknown characters based on appearance similarity. Only create new unknown characters when absolutely necessary.
   - Output format: Python dictionary {<character>: appearance information}.

4. **Scene**: Use one word or phrase to describe the scene in the current video (eg. "bedroom", "gym", "office", etc.).
   - Output format: Python string.

Special Rules:
- Use angle brackets to represent the characters eg. <Alice>, <Bob>, <robot>, <character_1>, etc.
- **Character identification priority**: 
  1. Use known character names if mentioned in conversation or clearly identifiable.
  2. If character is unknown, FIRST check if any previous unknown character (<character_1>, <character_2>, etc. from earlier clips) matches the appearance - reuse that character name.
  3. Only create a NEW unknown character (<character_X>) if no previous unknown character matches.
  4. Minimize the total number of unknown characters across all clips.
- If an unknown character is later identified, add an equivalence line at the **start of characters_behavior**. Then remove its information from character_appearance and replace it with the real name: 
  Example: "Equivalence: <character_1>, <Alice>"
- Include the robot (<robot>) if present:
  - It wears black gloves and has no visible face (it holds the camera).
  - Describe its behavior and conversation.
  - Do NOT include robot in character appearance information, but include it in characters_behavior and conversation.
- All characters' name mentioned in behaviors and conversation must exists in character appearance. 
- Maintain strict chronological order.
- Avoid repetition in both behavior and conversation.
- If no behavior or conversation is observed, return an empty list for characters_behavior and conversation.

Example Output:
Return a Python dictionary with exactly four keys:
{
    "characters_behavior": [
        "<Alice> enters the room.", 
        "<Alice> sits with <Bob> side by side on the couch.", 
        "<Bob> watches TV.", 
        "<robot> puts the coffee on the table."
    ],
    "conversation": [
        ["<Alice>", "Hello, my name is Alice."], 
        ["<Bob>", "Hi, I'm Bob. Nice to meet you."]
    ], 
    "character_appearance": {
      "<Alice>": "female, fat, ponytail, wear glasses, short-sleeved shirt, blue jeans, white sneakers", 
      "<Bob>": "male, thin, short hair, no glasses, black jacket, black pants, black shoes"
    }, 
    "scene": "bedroom"
}

Checklist: 
- [ ] Output is a JSON object.
- [ ] Dictionary has exactly 4 keys: "characters_behavior", "conversation", "character_appearance", "scene".
- [ ] No duplicate or repetitive entries in behavior or conversation.
"""


prompt_extract_triples = """
You are given a list of action sentences describing character behavior.  
Convert each sentence into triples of the form:

[target, content, source]

Return ONLY a valid JSON array (list of lists). No explanation.

### OUTPUT FORMAT
- Strict JSON only: double quotes, no trailing commas.
- Each triple: [target, content, source]
- Preserve input order.

### RULES
1. TARGET & SOURCE (Subject and Object)
- May be characters (with angle brackets) or objects/entities.
- Copy subjects verbatim (e.g., "<robot>", "coffee").
- Use `null` if no source exists.

2. CONTENT (Predicate)
- Must be the verb/action or relationship.
- Use **base form or present participle** ("walks", "puts", "looking").
- Include auxiliary verbs/prepositions when relevant ("picks up", "turns left", "looks at").
- Merge direction/position into the verb:
  - "<Lily> turns left" → ["<Lily>", "turns left", null]
  - "<robot> moves forward" → ["<robot>", "moves forward", null]
- Merge body parts into the verb:
  - "<Alice> hits <Bob>'s head" → ["<Alice>", "hits head", "<Bob>"]
  - "<Emma> touches <David>'s shoulder" → ["<Emma>", "touches shoulder", "<David>"]
- Communication actions: encode directly
  - ["<Alice>", "asks", "<Bob>"]
  - ["<Emma>", "greets", "<David>"]
  - Do NOT create abstract objects ("question", "message").
- State changes: use verbs like "is on", "becomes", "changes to".
- Prefer completed actions ("puts") over partial ones ("is putting").

3. OBJECT IDENTIFICATION
- Objects = nouns (physical things, abstract concepts, named items).
- Format: noun or noun#attribute or noun@<character>.
- Singularize plurals ("books" → "book").
- Keep named objects verbatim ("bottle of Nescafe").
- Split compound objects into separate triples.
- Use `null` if no object is extractable.
  - Example: "<Harry> walks" → ["<Harry>", "walk", null]

4. ATTRIBUTES (#)
- Attributes must be identity-defining: color, material, shape, size, brand/type.
- Example: "mug#white", "bag#leather".
- Do NOT encode location/position as attributes.

5. OWNERSHIP (@)
- Use `noun@<character>` for personal possessions:
  - Devices: phone, wallet, keys, watch, glasses
  - Clothing/accessories: jacket, bag, hat
- Triggered by possessive pronouns ("her phone", "his bag").
- Do NOT use for shared/public objects (table, chair, mug, door, basketball).

6. PRONOUNS
- NEVER use pronouns ("her", "his", "their").
- Replace with explicit character/object names.

7. MULTIPLE RELATIONS
- Split sentences with multiple subjects, contents (verbs), or objects into separate triples.
- **Multiple subjects**: Each subject gets its own triple with the same content and object.
  Example: "<Alice> and <Bob> exit" →
    ["<Alice>", "exit", null],
    ["<Bob>", "exit", null]
- **Multiple contents (verbs)**: Each verb gets its own triple with the same subject and object.
  Example: "<Alice> walks and talks" →
    ["<Alice>", "walks", null],
    ["<Alice>", "talks", null]
- **Multiple objects**: Each object gets its own triple with the same subject and content.
  Example: "<Alice> picks up the book and the pen" →
    ["<Alice>", "picks up", "book"],
    ["<Alice>", "picks up", "pen"]

8. DEDUPLICATION
- Keep only distinct, meaningful actions.
- Avoid redundant states implied by stronger actions.

9. STATE REPRESENTATION
- Allowed with object as subject:
  - "<robot> puts coffee on table" →
    ["<robot>", "puts", "coffee"],
    ["coffee", "is on", "table"]

10. FALLBACK
- If unsure, default to minimally transformed [target, content, source].

### EXAMPLE

Input:
[
  "<Michael> pats <Susan>'s shoulder and smiles.",
  "<robot> places the red cup on the counter.",
  "<Tom> asks <Mary> about the meeting.",
  "<Lisa> dances and sings.",
  "<John> takes his wallet and keys from the drawer."
]
Output:
[
  ["<Michael>", "pats shoulder", "<Susan>"],
  ["<Michael>", "smiles", null],
  ["<robot>", "places", "cup#red"],
  ["cup#red", "is on", "counter"],
  ["<Tom>", "asks", "<Mary>"],
  ["<Lisa>", "dances", null],
  ["<Lisa>", "sings", null],
  ["<John>", "takes", "wallet@<John>"],
  ["<John>", "takes", "keys@<John>"]
]

Now convert the following lines into triples:
"""


prompt_summary = """
You are given a sequence of video clips (each clip is 30 seconds long) with scene descriptions and character behaviors.
Your task is to summarize this information into a concise, narrative paragraph.

### INPUT FORMAT
The input consists of multiple clips, each with:
- Clip ID and Scene name
- A list of character behaviors (actions and events)

### OUTPUT REQUIREMENTS
- Write a single, coherent paragraph (3-5 sentences)
- Describe the sequence of events in chronological order
- Include key actions, character interactions, and scene transitions
- Use natural, flowing language (not a bulleted list)
- Focus on the main narrative flow and significant events
- Keep character names as provided (e.g., <character_1>, <robot>)
- Do not include clip numbers or scene labels in the summary
- There might be conflict or misleading information provided, you should be able to handle it and provide a coherent summary.

Now summarize the following clips:
"""


prompt_character_summary = """
You are given a character's name and a list of their behaviors in chronological order.

Your task is to summarize the character's attributes: 
- Personality (eg. confident, nervous)
- Role/profession (eg. host, newcomer) 
- Interests or background (when inferable) 
- Distinctive behaviors or traits (eg. speaks formally, fidgets). 
Avoid restating visual facts—focus on identity construction.

For each attribute, you should also provide a confidence score between 0 and 100. 
If the confidence score is less than 50, you should not include the attribute in the output.

Output a JSON dictionary (key: attribute, value: confidence score). 
Example: {"student": 90, "enthusiastic": 80, "likes to read": 70, "professional": 50}
"""


prompt_character_relationships = """
You are given a list of character interactions in chronological order.
Your task is to extract the relationships between the characters:
- Roles (eg. friends, colleagues, host-guest, teacher-student, parent-child, etc.)
- Attitudes/Emotions (eg. respect, dislike, friendly, etc.)
- Power dynamics (eg. who leads, equal, etc.)
- Evidence of cooperation
- Exclusion, conflict, competition, etc. 

Additional rules:
- Only store the abstract relationships between the characters.
- Do NOT include any actual actions or summary of actions in the output (eg. <Alice> speaks with <Bob>, <Alice> plays games with <Bob>, etc.). 
- Do not generate repetitive or symmetric information. 

For each relationship, you should also provide a confidence score between 0 and 100.
If the confidence score is less than 50, you should not include the relationship in the output.
It is acceptable to only generate a few relationships if you don't have enough information.

Output a JSON array (list of lists). 
Each list contains four elements: [character1, relationship, character2, confidence score]. 
Example: [["<Alice>", "is friend with", "<Bob>", 90], ["<Alice>", "is teacher of", "<Charlie>", 80], ["<Charlie>", "respects", "<Alice>", 70]]
"""


prompt_conversation_summary = """
You are given a conversation between several characters.

Your tasks: 

1. **Summary**
- Summarize the key topics, decisions, or outcomes discussed in the conversation.
- Write 2-4 concise sentences covering the main themes and important points.
- Focus on what was discussed and decided, not on individual statements.
- Output format: JSON string value.

2. **Character Attributes**
- Extract each character's attributes revealed through their dialogue and interaction style.
- Focus on: personality traits, role/profession, interests, background information (when mentioned).
- **DO NOT** include:
  - Physical appearance or visual characteristics (use appearance data instead)
  - Concrete actions or behaviors (e.g., "asked a question", "walked away")
  - Temporary emotional states (use persistent personality traits instead)
  - Information not directly supported by the conversation
- Output format: JSON array of arrays. Each inner array: [character, attribute, confidence_score].
- Confidence scores range from 0-100. Only include attributes with confidence >= 50.
- Avoid redundant or overly similar attributes (e.g., don't include both "friendly" and "kind" unless distinctly different).
- Use angle brackets for character names (e.g., "<Alice>", "<Bob>").

3. **Character Relationships**
- Extract abstract relationships between characters based on their dialogue interactions.
- Include: roles (friends, colleagues, teacher-student, etc.), attitudes (respect, dislike, etc.), 
  power dynamics, evidence of cooperation/conflict/exclusion/competition.
- **DO NOT** include:
  - Specific actions or events (e.g., "<Alice> speaks with <Bob>", "<Alice> asked <Bob> about X")
  - Temporary interactions (focus on underlying relationship patterns)
  - Dialogue content or topics discussed (focus on the relationship itself, not what they discussed)
- Output format: JSON array of arrays. Each inner array: [character1, relationship, character2, confidence_score].
- Confidence scores range from 0-100. Only include relationships with confidence >= 50.
- Do not generate symmetric duplicates (if "<Alice> respects <Bob>" is included, don't automatically include reverse unless explicitly different).
- It is acceptable to generate only a few relationships if there is insufficient information.

### EDGE CASES
- If conversation has only one character speaking: focus on their attributes, skip relationships.
- If conversation is empty or unclear: return empty arrays for attributes and relationships, provide a brief summary noting the issue.
- If character names are ambiguous: use the names as provided in the conversation.

### OUTPUT FORMAT
Return a JSON dictionary with exactly three keys: "summary", "character_attributes", "characters_relationships".

### EXAMPLE OUTPUT
{
  "summary": "Alice and Bob discussed their upcoming project. They agreed on a timeline and assigned tasks. Bob expressed concerns about the deadline, which Alice addressed by suggesting additional resources.",
  "character_attributes": [
    ["<Alice>", "organized", 85],
    ["<Alice>", "problem-solver", 75],
    ["<Bob>", "detail-oriented", 80],
    ["<Bob>", "cautious", 70]
  ],
  "characters_relationships": [
    ["<Alice>", "collaborates with", "<Bob>", 90],
    ["<Bob>", "trusts", "<Alice>", 75]
  ]
}

### BAD EXAMPLE (What NOT to do)
{
  "summary": "The conversation is about the characters' attributes and relationships.",
  "character_attributes": [
    ["<Alice>", "asked a question", 90],  // WRONG: This is an action, not an attribute
    ["<Bob>", "has brown hair", 80]       // WRONG: This is appearance, not attribute
  ],
  "characters_relationships": [
    ["<Alice>", "spoke with", "<Bob>", 90],     // WRONG: This is an action
    ["<Alice>", "discussed the project", "<Bob>", 85]  // WRONG: This is dialogue content, not relationship
  ]
}

Now summarize the following conversation:
"""


#--------------------------------
# Search Prompts
#--------------------------------

prompt_parse_query = """
You are a query parser for a knowledge graph system that stores video information in a hierarchical structure.

## GRAPH STRUCTURE

**HIGH-LEVEL EDGES (clip_id=0)**: Character attributes/relationships
- Format: `["<Alice>", "confident", null]` or `["<Alice>", "is friend with", "<Bob>"]`
- **Limited quantity** (<10 per query) - allocate 5-10 max when needed, fewer otherwise
- Use for: character traits, relationships, "who is" queries

**LOW-LEVEL EDGES (clip_id>0)**: Specific actions/states with scene info
- Format: `["<Alice>", "picks up", "coffee"]` or `["coffee", "is on", "table"]`
- Most abundant source - allocate 30-45 for action-focused queries
- Use for: specific actions, temporal/spatial queries ("what did X do", "where is X")

**CONVERSATIONS**: Dialogue transcripts `[speaker, text]` pairs
- Allocate 10-45 based on query needs
- Use for: "why" questions, dialogue content, causal reasoning

## YOUR TASK

Given a query and budget `k=50`, output:

1. **Query triple** `[source, content, target, source_weight, content_weight, target_weight]`:
   - Use `null` for missing components, normalize to graph format (angle brackets for characters)
   - **Assign weights** (0.0-1.0):

**Weight Rules**:
- **High (0.7-1.0)**: Specific character/object names (e.g., "Alice", "coffee", "the red cup") - use 0.9-1.0 for critical entities
- **Medium (0.4-0.7)**: General objects/locations (e.g., "cup", "room") - use 0.5-0.7 for context
- **Low (0.1-0.4)**: What we're searching for - question marks ("?"), relationship terms ("relationship", "friendship"), unknown actions - use 0.2-0.4 for search targets, 0.1-0.2 for vague terms

2. **Allocation** `{k_high_level, k_low_level, k_conversations}`:
   - Total must be ≤ 50
   - High-level: 5-10 max (limited availability)
   - Low-level: 30-45 for action queries
   - Conversations: 10-45 based on needs

3. **speaker_strict**: 
   - Set to `["<Alice>", "<Bob>"]` when query asks about dialogue between specific speakers
   - Set to `null` otherwise

4. **spatial_constraint**: Location string if query mentions specific place, else `null`

## EXAMPLES

**Example 1**: "What is Alice's relationship with Bob?"
```json
{
  "query_triple": ["<Alice>", "relationship", "<Bob>", 0.95, 0.2, 0.95], 
  "spatial_constraint": null, 
  "speaker_strict": null, 
  "allocation": {"k_high_level": 10, "k_low_level": 10, "k_conversations": 30, "total_k": 50, "reasoning": "Relationship query - use high-level for relationships, conversations for evidence"}
}
```

**Example 2**: "Why did Alice leave the room?"
```json
{
  "query_triple": ["<Alice>", "leaves", "room", 0.95, 0.5, 0.6], 
  "spatial_constraint": "room", 
  "speaker_strict": null, 
  "allocation": {"k_high_level": 8, "k_low_level": 12, "k_conversations": 30, "total_k": 50, "reasoning": "Why query - prioritize conversations for motivations"}
}
```

**Example 3**: "What did Alice do with the coffee in the kitchen?"
```json
{
  "query_triple": ["<Alice>", "?", "coffee", 0.95, 0.15, 0.9], 
  "spatial_constraint": "kitchen", 
  "speaker_strict": null, 
  "allocation": {"k_high_level": 5, "k_low_level": 38, "k_conversations": 7, "total_k": 50, "reasoning": "Action query - prioritize low-level edges"}
}
```

**Example 4**: "What did Alice and Bob discuss?"
```json
{
  "query_triple": ["<Alice>", "discusses", "<Bob>", 0.9, 0.3, 0.9], 
  "spatial_constraint": null, 
  "speaker_strict": ["<Alice>", "<Bob>"], 
  "allocation": {"k_high_level": 2, "k_low_level": 3, "k_conversations": 45, "total_k": 50, "reasoning": "Dialogue query - prioritize conversations with specific speakers"}
}
```

**Example 5**: "Where is the red cup?"
```json
{
  "query_triple": ["cup#red", "is at", "?", 0.9, 0.4, 0.15], 
  "spatial_constraint": null, 
  "speaker_strict": null, 
  "allocation": {"k_high_level": 2, "k_low_level": 40, "k_conversations": 8, "total_k": 50, "reasoning": "Spatial query - prioritize low-level edges for location"}
}
```

Now parse the following query and allocate k=50:
"""


prompt_semantic_episodic = """
You are a reasoning system that evaluates whether information extracted from a knowledge graph is sufficient to answer a question.

The system processes video information in three layers:
1. **Video**: Videos are split into 30-second segments, each assigned a unique clip_id (1, 2, 3, ...)
2. **Text**: Each segment's text descriptions (behaviors, conversations, scenes) are stored by clip_id
3. **Graph**: Text is converted into graph edges with two types:
   - **High-level** : Abstract attributes/relationships
   - **Low-level** : Specific actions/states with temporal and spatial information
   Each edge's clip_id links back to its original video segment. 
All the current information provided is from the graph.

Input format: 
1. **Parentheses (X)**: Confidence scores (0-100) in high-level information, indicating reliability.
  Example: Anna is: health-conscious (80) means 80% confidence.
2. **Square brackets [X]**: Clip IDs indicating timestamps. Each clip = 30 seconds: clip 1 = 0-30s, clip 2 = 30-60s, clip 3 = 60-90s, etc.
  Applies to both low-level actions and conversation messages.
  Example: [1] Anna walk. (ping-pong room) means this occurred during clip 1 (0-30 seconds).

Decision criteria: 
1. Answer directly ([Answer]) when the current information provides a clear, complete answer.
2. Search text memory ([Search]) when the current information is incomplete or ambiguous.

Output the answer in the format: 
Action: [Answer] or [Search]
Content: <your answer here> or <updated query>

If the action is [Search], provide an updated query that would help retrieve the missing information. The query should be more specific or focus on the aspects that are unclear or missing from the current search results. Use natural language and be precise about what information you need.

Examples:

Question: Who is the best friend of Alice?
Output:
Action: [Answer]
Content: Bob is Alice's best friend.

Question: Why did Alice leave the room?
Output:
Action: [Search]
Content: What happened before Alice left the room that caused her to leave?
"""


prompt_semantic_video = """
You are a reasoning system that evaluates whether information extracted from a knowledge graph is sufficient to answer a question.

You will be provided with extracted knowledge from the video graph, including three components: high-level information (character attributes/relationships), low-level information (actions/states), and conversations.

Input format: 
- **Parentheses (X)**: Confidence scores (0-100) in high-level information, indicating reliability.
  Example: Anna is: health-conscious (80) means 80% confidence.
- **Square brackets [X]**: Clip IDs indicating timestamps. Each clip = 30 seconds: clip 1 = 0-30s, clip 2 = 30-60s, clip 3 = 60-90s, etc.
  Applies to both low-level actions and conversation messages.
  Example: [1] Anna walk. (ping-pong room) means this occurred during clip 1 (0-30 seconds).

Decision criteria: 
1. Answer directly ([Answer]) when the current graph information provides a clear answer to the question. You should make reasonable deductions and inferences from the available information when appropriate. If the information is sufficient to answer the question (even if not explicitly stated verbatim), choose [Answer].
2. Search video memory ([Search]) only when the extracted information is fundamentally insufficient and cannot support a reasonable answer through deduction.

Output format: 
Action: [Answer] or [Search]
Content: <your answer here> or [clip_id1, clip_id2, ...]
Summary: <only present when Action is [Search] - summary of extracted information from the graph>

If the action is [Search]:
- **Content**: Provide a list of video clip IDs (as integers) ranked by relevance: [clip_id1, clip_id2, ...]
- **Summary**: Provide a concise summary of extracted graph information relevant to the question, including key events, character information, conversations, and temporal/spatial context.

If the action is [Answer], do not include a Summary field.

Examples:

Question: What is the relationship between Anna and Susan?
Extracted information: High-level: Anna competes with Susan (85). Anna is competitive (90). Susan is competitive (88). Low-level: [12] Anna challenges Susan to a game. [15] Anna and Susan prepare for competition. Conversations: Conversation 1: Anna and Susan discuss their upcoming game, with Anna expressing confidence in winning.
Output:
Action: [Answer]
Content: Anna and Susan are competitors. Both are competitive individuals, and Anna has challenged Susan to a game.

Question: What did Anna decide to drink before the game?
Extracted information: High-level: Anna is health-conscious (80). Anna prefers water (85). Low-level: [15] Anna picks up Anna's water bottle. [16] Susan picks up Susan's sports drink. Conversations: Conversation 2: Anna says "I just want a bottle of water. That's fine. No sports soda for me." Susan responds "you never drink sports soda, and just mineral water."
Output:
Action: [Answer]
Content: Anna decided to drink water before the game.

Question: Where did Anna and Susan have their conversation about the game?
Extracted information: High-level: (no location attributes found) Low-level: [10] Anna walks to ping-pong room. [12] Anna and Susan stand in ping-pong room. Conversations: Conversation 1: Anna and Susan discuss their upcoming game. [Clip 12]
Output:
Action: [Answer]
Content: Anna and Susan had their conversation about the game in the ping-pong room.

Question: What was the exact expression on Anna's face when she received the gift?
Extracted information: High-level: (no facial expression information) Low-level: [15] Bob gives Anna wrapped gift box. [16] Anna unwraps gift box. Conversations: (no relevant conversations)
Output:
Action: [Search]
Content: [15, 16]
Summary: The graph shows Bob giving Anna a wrapped gift box at clip 15, and Anna unwrapping it at clip 16. However, the graph does not contain information about Anna's specific facial expression or micro-expressions, which requires visual analysis of the video frames.

Question: Why did Alice suddenly leave in the middle of the conversation?
Extracted information: High-level: Alice talks to Bob (75) Low-level: [20] Alice walks out of kitchen. Conversations: Conversation 3: Alice and Bob discuss work topics. The conversation ends at clip 19. [Clip 19]
Output:
Action: [Search]
Content: [18, 19, 20, 21]
Summary: The graph shows Alice leaving the kitchen at clip 20, and a conversation with Bob ending at clip 19. However, the specific reason for Alice's sudden departure is not captured in the extracted information - the conversation content and context leading to the departure are unclear and require viewing the video.
"""


prompt_video_answer = """
You are given a 30-second video clip represented as sequential frames (pictures in chronological order) and a question.

**Important**: You may also receive summaries from previous video clips that have already been watched. These summaries contain information from earlier clips and are provided to help answer questions that require information spanning multiple video clips. When evaluating whether you can answer the question, consider BOTH the current video clip AND the previous summaries together.

Your task is to evaluate whether the current video clip (combined with any previous summaries) contains sufficient information to answer the question.

Decision criteria:
1. **Answer directly ([Answer])** when:
   - The current video (possibly combined with previous summaries) clearly shows the answer to the question
   - All necessary information is available from the current clip and/or previous summaries
   - The answer is unambiguous and complete
   - Example: Question asks "What color is Alice's shirt?" and the current video clearly shows Alice wearing a red shirt
   - Example: Question asks "What happened after Alice received the gift?" and the current video shows the answer, even though previous summaries showed her receiving it

2. **Search next video ([Search])** when:
   - The current video AND previous summaries together are still missing critical information
   - The answer requires events that occur in clips not yet watched
   - The information is ambiguous or unclear even when combining current video with previous summaries
   - The video shows partial information but key details are still missing after considering previous summaries
   - Example: Question asks "Why did Alice leave?" and the current video shows Alice leaving, but neither the current video nor previous summaries show what caused her to leave

Output format:
Action: [Answer] or [Search]
Content: <your answer here> or <summary of what the video shows>

- If Action is [Answer]: Provide a clear, direct answer to the question based on the current video and/or previous summaries
- If Action is [Search]: Provide a summary describing what the current video shows. This summary will be passed to the next video clip. Focus on key events, characters, objects, or actions that might be relevant for answering the question

Examples:

Question: Who is Alice talking to in this clip?
Previous summaries: None (first clip)
Video shows: Alice and Bob having a conversation in the kitchen
Output:
Action: [Answer]
Content: Alice is talking to Bob.

Question: Why did Alice leave the room?
Previous summaries: Clip 1: Alice and Bob are discussing a project in the office. Clip 2: Bob suggests taking a break.
Video shows: Alice walking out of the kitchen, but no clear reason visible
Output:
Action: [Search]
Content: Alice walks out of the kitchen. The reason for leaving is still unclear from the current video and previous summaries.

Question: What did Alice do after receiving the gift?
Previous summaries: Clip 1: Bob gives Alice a wrapped gift box. Clip 2: Alice unwraps the gift and sees it's a book.
Video shows: Alice reading the book and thanking Bob
Output:
Action: [Answer]
Content: After receiving the gift, Alice read the book and thanked Bob.

Question: What is Bob holding?
Previous summaries: None (first clip)
Video shows: Bob clearly holding a red coffee cup
Output:
Action: [Answer]
Content: Bob is holding a red coffee cup.

Question: What did Alice say to Bob when she first saw him today?
Previous summaries: Clip 1: Alice enters the room and sees Bob.
Video shows: Alice's mouth moving but no subtitles or clear audio
Output:
Action: [Search]
Content: Alice appears to be speaking to Bob, but the conversation content is unclear from the video. The previous summary indicates this is when Alice first saw Bob.
"""


prompt_video_answer_final = """
You are given a 30-second video represented as sequential frames (pictures in chronological order) and a question. 

Your task is to answer the question based on the video and the previous video summaries. If the given information is insufficient or missing critical details, you can make reasonable guess. 

Only output the answer, with no additional explanation.
"""
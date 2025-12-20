
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
- Summarize the conversation in a few sentences.
- Output format: Python string.

2. **Character's Attributes**
- Describe each character's attributes: personality, role, interests, background, etc.
- Output format: Python dictionary {<character>: attributes}.

3. **Character Relationships**
- Describe the relationships between the characters: roles, attitudes, power dynamics, evidence of cooperation, exclusion, conflict, competition, etc.
- Output format: Python dictionary {<character>: relationships}.
"""


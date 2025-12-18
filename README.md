# HiViM-simple

Video processing pipeline for building episodic and semantic memory from video frames.

## Quick Start

1. **Extract frames with subtitles:**
   ```bash
   python preprocessing/add_subtitles_and_extract_frames.py
   ```

2. **Process videos to build memory:**
   ```bash
   python process_full_video.py 1-20  # Process first 20 videos
   ```

## Structure

- `preprocessing/` - Video processing and frame extraction
- `classes/` - Graph data structures (characters, objects, edges)
- `utils/` - LLM/MLLM utilities and prompts
- `data/frames/` - Extracted video frames
- `data/episodic_memory/` - Generated episodic memory JSON files
- `data/semantic_memory/` - Generated graph pickle files


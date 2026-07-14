#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

# Add src/ to path so we can import agent_guidance_mcp
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_guidance_mcp.catalog import build_catalog

def main():
    print("Building standards catalog...")
    standards_root = Path(__file__).resolve().parents[1]
    catalog = build_catalog(standards_root)
    
    skills = [entry for entry in catalog.entries if entry.kind == "skill"]
    print(f"Found {len(skills)} skills in catalog.")
    
    if not skills:
        print("No skills found. Exiting.")
        sys.exit(1)
        
    print("Loading sentence-transformers/all-MiniLM-L6-v2...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    print("Generating embeddings...")
    embeddings_map = {}
    for entry in skills:
        content = catalog.read_entry(entry.identifier, optimize=False)
        # Combine title, description, and first 1000 chars of content for the document representation
        text_to_embed = f"Title: {entry.title}\nDescription: {entry.description}\nContent: {content[:1000]}"
        vector = model.encode(text_to_embed, normalize_embeddings=True)
        embeddings_map[entry.identifier] = vector.tolist()
        print(f"  Embedded skill: {entry.identifier}")
        
    output_path = Path(__file__).resolve().parents[1] / "src" / "agent_guidance_mcp" / "skills_embeddings.json"
    print(f"Writing embeddings to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(embeddings_map, f)
        
    print("Successfully completed!")

if __name__ == "__main__":
    main()

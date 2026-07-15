#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

# Add src/ to path so we can import agent_guidance_mcp
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_guidance_mcp.catalog import build_catalog
from agent_guidance_mcp.embeddings import embed_text_for_entry, hash_text

def main():
    print("Building standards catalog...")
    standards_root = Path(__file__).resolve().parents[1]
    catalog = build_catalog(standards_root)

    # F4-A: embed every entry (skills AND documents) so semantic ranking is not
    # limited to skills.
    entries = list(catalog.entries)
    print(f"Found {len(entries)} entries in catalog.")

    if not entries:
        print("No entries found. Exiting.")
        sys.exit(1)

    model_name = "intfloat/multilingual-e5-small"
    print(f"Loading {model_name}...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name)

    print("Generating embeddings...")
    embeddings_map: dict[str, list[float]] = {}
    hashes: dict[str, str] = {}
    for entry in entries:
        content = catalog.read_entry(entry.identifier, optimize=False)
        # E5 requires a "passage: " prefix for document-side text.
        text_to_embed = embed_text_for_entry(entry.title, entry.description, content)
        vector = model.encode(text_to_embed, normalize_embeddings=True)
        embeddings_map[entry.identifier] = vector.tolist()
        # Store a content hash so runtime can detect staleness (F2).
        hashes[entry.identifier] = hash_text(text_to_embed)
        print(f"  Embedded {entry.kind}: {entry.identifier}")

    output_path = Path(__file__).resolve().parents[1] / "src" / "agent_guidance_mcp" / "skills_embeddings.json"
    print(f"Writing embeddings to {output_path}...")
    data: dict[str, object] = {"__meta__": {"version": 1, "hashes": hashes}}
    data.update(embeddings_map)
    tmp_path = output_path.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp_path, output_path)

    print("Successfully completed!")

if __name__ == "__main__":
    main()

import re
from typing import List, Dict, Any

def chunk_text(
    text: str,
    metadata: Dict[str, Any],
    chunk_size_words: int = 250,
    overlap_words: int = 40
) -> List[Dict[str, Any]]:
    """
    Split text into logical, coherent semantic chunks preserving metadata.
    Avoids arbitrary word cutting; splits along numbered items, sections, or sentences.
    """
    chunks = []
    
    # Check if text contains numbered lists (e.g. "1. B.E. Computer Science...", "2. B.Tech...")
    list_items = re.split(r"(?=\n\d+\.\s+)", text)
    if len(list_items) > 2:
        # Structured list mode
        header = list_items[0].strip()
        current_chunk = header
        
        for item in list_items[1:]:
            item_clean = item.strip()
            if len((current_chunk + "\n" + item_clean).split()) > chunk_size_words:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = header + "\n" + item_clean
            else:
                current_chunk += "\n" + item_clean
                
        if current_chunk:
            chunks.append(current_chunk.strip())
    else:
        # Sliding sentence window mode
        sentences = re.split(r"(?<=[.!?])\s+", text)
        current_words = []
        
        for sentence in sentences:
            sentence_words = sentence.split()
            if len(current_words) + len(sentence_words) > chunk_size_words:
                if current_words:
                    chunks.append(" ".join(current_words))
                    # Retain overlap from end
                    current_words = current_words[-overlap_words:] + sentence_words
                else:
                    chunks.append(sentence)
            else:
                current_words.extend(sentence_words)
                
        if current_words:
            chunks.append(" ".join(current_words))

    # Format into chunk records with metadata
    chunk_records = []
    for idx, content in enumerate(chunks):
        if not content.strip():
            continue
        chunk_meta = dict(metadata)
        chunk_meta["chunk_index"] = idx
        chunk_meta["token_count"] = len(content.split())
        chunk_records.append({
            "chunk_index": idx,
            "content": content,
            "token_count": len(content.split()),
            "metadata": chunk_meta
        })
        
    return chunk_records

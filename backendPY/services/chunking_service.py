import abc
import re
import uuid
import logging
from typing import List, Dict, Any

logger = logging.getLogger("chunking_service")

def count_tokens(text: str) -> int:
    """Helper utility to count tokens with tiktoken, falling back to an approximate ratio."""
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except ImportError:
        # Approximate counting: 1 word ~ 1.3 tokens
        return int(len(text.split()) * 1.3)

class ChunkingStrategy(abc.ABC):
    @abc.abstractmethod
    def split_text(
        self,
        text: str,
        target_tokens: int,
        max_tokens: int,
        overlap_tokens: int,
        document_name: str,
        page_number: int
    ) -> List[str]:
        """Splits the text into layout-aware semantic chunks."""
        pass

class LayoutAwareChunkingStrategy(ChunkingStrategy):
    """
    Layout-aware chunking strategy:
    - Parses text into structure blocks (headings, paragraphs, lists).
    - Tracks heading hierarchy (Section Path).
    - Groups blocks until they hit target token limit.
    - Applies sliding window overlaps.
    - Prepends metadata headers.
    """
    def split_text(
        self,
        text: str,
        target_tokens: int,
        max_tokens: int,
        overlap_tokens: int,
        document_name: str,
        page_number: int
    ) -> List[str]:
        if not text.strip():
            return []

        # 1. Parse lines into layout blocks
        lines = text.split("\n")
        blocks = []
        current_block = []
        
        # Section path tracking state
        section_hierarchy = ["", "", ""] # [h1, h2, h3]

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current_block:
                    blocks.append(self._classify_block(current_block, section_hierarchy))
                    current_block = []
                continue

            # Heading checks
            h_match = re.match(r"^(\#{1,6})\s+(.*)$", stripped)
            if h_match:
                # Heading level
                level = len(h_match.group(1))
                title = h_match.group(2).strip()
                
                # Flush previous block
                if current_block:
                    blocks.append(self._classify_block(current_block, section_hierarchy))
                    current_block = []
                
                # Update hierarchy
                if level == 1:
                    section_hierarchy = [title, "", ""]
                elif level == 2:
                    section_hierarchy[1] = title
                    section_hierarchy[2] = ""
                else:
                    section_hierarchy[2] = title
                
                blocks.append({
                    "type": "heading",
                    "text": stripped,
                    "section_path": self._get_section_path(section_hierarchy)
                })
                continue
            
            # List check
            if re.match(r"^(\*|\-|\d+\.)\s+", stripped):
                if current_block:
                    blocks.append(self._classify_block(current_block, section_hierarchy))
                    current_block = []
                blocks.append({
                    "type": "list_item",
                    "text": stripped,
                    "section_path": self._get_section_path(section_hierarchy)
                })
                continue

            current_block.append(stripped)

        if current_block:
            blocks.append(self._classify_block(current_block, section_hierarchy))

        # 2. Group blocks into chunks
        chunks = []
        current_chunk_text = ""
        current_section_path = "Introduction"
        overlap_buffer = ""

        for block in blocks:
            block_text = block["text"]
            block_section_path = block["section_path"] or current_section_path
            
            # Compute potential new content
            potential_content = block_text
            if current_chunk_text:
                potential_content = current_chunk_text + "\n\n" + block_text
            
            # Metadata injection header preview
            header = f"Document: {document_name}\nPage: {page_number}\nSection Path: {block_section_path}\n---\n"
            potential_full_text = header + potential_content
            
            tokens = count_tokens(potential_full_text)
            
            if tokens <= target_tokens:
                current_chunk_text = potential_content
                current_section_path = block_section_path
            else:
                # If block is exceptionally large, split it with sliding window
                if count_tokens(header + block_text) > max_tokens:
                    # Flush active chunk first
                    if current_chunk_text:
                        chunks.append(f"Document: {document_name}\nPage: {page_number}\nSection Path: {current_section_path}\n---\n{current_chunk_text}")
                        current_chunk_text = ""
                    
                    # Split massive block using sliding word window
                    chunks.extend(self._split_massive_text(
                        text=block_text,
                        target_tokens=target_tokens,
                        overlap_tokens=overlap_tokens,
                        header=header
                    ))
                else:
                    # Flush previous chunk
                    if current_chunk_text:
                        chunks.append(f"Document: {document_name}\nPage: {page_number}\nSection Path: {current_section_path}\n---\n{current_chunk_text}")
                    
                    # Generate overlap from previous text
                    overlap_buffer = self._extract_overlap_text(current_chunk_text, overlap_tokens)
                    
                    # Start new chunk
                    if overlap_buffer:
                        current_chunk_text = overlap_buffer + "\n\n" + block_text
                    else:
                        current_chunk_text = block_text
                    current_section_path = block_section_path

        # Flush trailing content
        if current_chunk_text:
            header = f"Document: {document_name}\nPage: {page_number}\nSection Path: {current_section_path}\n---\n"
            chunks.append(header + current_chunk_text)

        return chunks

    def _classify_block(self, lines: List[str], hierarchy: List[str]) -> Dict[str, Any]:
        text = " ".join(lines)
        return {
            "type": "paragraph",
            "text": text,
            "section_path": self._get_section_path(hierarchy)
        }

    def _get_section_path(self, hierarchy: List[str]) -> str:
        parts = [p for p in hierarchy if p]
        return " > ".join(parts) if parts else "Introduction"

    def _extract_overlap_text(self, text: str, overlap_tokens: int) -> str:
        """Extracts the last overlap_tokens tokens from text (using word counts roughly)."""
        words = text.split()
        if not words:
            return ""
        # 1 token ~ 0.75 words. overlap_tokens * 0.75 gives rough overlap words count.
        words_count = int(overlap_tokens * 0.75)
        if words_count >= len(words):
            return text
        return " ".join(words[-words_count:])

    def _split_massive_text(self, text: str, target_tokens: int, overlap_tokens: int, header: str) -> List[str]:
        """Splits text that exceeds limits using a token-based sliding window."""
        words = text.split()
        chunks = []
        
        header_tokens = count_tokens(header)
        available_tokens = target_tokens - header_tokens
        
        # Word limits
        words_per_chunk = int(available_tokens * 0.75)
        overlap_words = int(overlap_tokens * 0.75)
        
        if words_per_chunk <= 0:
            words_per_chunk = 50
        if overlap_words >= words_per_chunk:
            overlap_words = words_per_chunk // 5

        i = 0
        while i < len(words):
            segment = " ".join(words[i : i + words_per_chunk])
            chunks.append(header + segment)
            i += (words_per_chunk - overlap_words)
            
        return chunks

class ChunkingContext:
    def __init__(self, strategy: ChunkingStrategy):
        self._strategy = strategy

    def set_strategy(self, strategy: ChunkingStrategy):
        self._strategy = strategy

    def chunk_page(
        self,
        text: str,
        document_name: str,
        page_number: int,
        target_tokens: int = 500,
        max_tokens: int = 800,
        overlap_tokens: int = 100
    ) -> List[str]:
        return self._strategy.split_text(
            text=text,
            target_tokens=target_tokens,
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
            document_name=document_name,
            page_number=page_number
        )

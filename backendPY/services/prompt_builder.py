import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from services.retrieval_engine import RetrievedContext

logger = logging.getLogger("prompt_builder")

class PromptPackage(BaseModel):
    system_prompt: str
    user_prompt: str
    token_budget: int
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PromptBuilder:
    @classmethod
    def build_package(
        cls,
        retrieved_context: RetrievedContext,
        conversation_summary: Optional[str] = None,
        question: str = "",
        token_budget: int = 4000,
        mode: str = "detailed"
    ) -> PromptPackage:
        """
        Statelessly compiles the query, conversation history, and retrieval contexts into
        a strict prompt package containing role descriptors, citation parameters, and budget limits.
        """
        logger.info(f"Building PromptPackage for query: '{question}' in mode: '{mode}'")

        mode_instructions = {
            "summary": "Provide a concise summary of the key information.",
            "detailed": "Provide a detailed, comprehensive explanation covering all nuances.",
            "bullet_points": "Provide the response as a clear, organized list of bullet points.",
            "timeline": "Present the information in a chronological timeline structure.",
            "comparison_table": "Present the information as a structured comparison table.",
            "research_report": "Structure your response as a formal Research Report with an introduction, key findings, and analysis sections.",
            "executive_summary": "Structure your response as a high-level Executive Summary highlighting the key takeaways.",
            "technical_explanation": "Provide a precise, technical explanation suitable for developers or engineers.",
            "notebook_notes": "Format your response as informal, cataloged notebook study notes.",
            "flashcards": "Format your response as a set of Front/Back Flashcards (e.g. 'Flashcard 1:\nFront: ...\nBack: ...').",
            "question_answer": "Format the response as a series of direct questions and answers."
        }
        mode_instruction = mode_instructions.get(mode.lower(), mode_instructions["detailed"])

        # 1. System prompt detailing role constraints and citation formatting
        system_prompt = (
            "You are a document assistant.\n"
            "Answer ONLY using the retrieved document context.\n"
            "Never use your own knowledge.\n"
            "Never hallucinate.\n"
            "At the end of each sentence or paragraph that references information from a Context Block, append the corresponding bracketed citation number (e.g. [1] for Context Block 1, [2] for Context Block 2, etc.).\n"
            "If the answer cannot be verified from the retrieved document context, "
            "reply EXACTLY:\n"
            "'I couldn't find this information in the uploaded document.'\n"
            "Do not guess.\n"
            "Do not fabricate.\n"
            "Do not answer using general knowledge.\n"
            f"Format requirements: {mode_instruction}"
        )

        # 2. Handle empty retrieval fallback
        if not retrieved_context.retrieved_chunks:
            user_prompt = (
                "Document:\nNone\n\nPage:\nNone\n\nChunk:\nNone\n\nText:\nNone\n\n"
                f"Question:\n{question}"
            )
            return PromptPackage(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                token_budget=token_budget,
                metadata={"empty_retrieval": True}
            )

        # 3. Format user prompt with context, history summary, and question
        contexts_block_list = []
        for idx, chunk in enumerate(retrieved_context.retrieved_chunks):
            doc_name = retrieved_context.document_names[idx] if idx < len(retrieved_context.document_names) else "Document"
            page_num = retrieved_context.pages[idx] if idx < len(retrieved_context.pages) else 1
            chunk_id = list(retrieved_context.retrieval_scores.keys())[idx] if idx < len(retrieved_context.retrieval_scores) else f"chunk_{idx}"
            
            contexts_block_list.append(
                f"Context Block {idx+1}:\n"
                f"Document:\n{doc_name}\n\n"
                f"Page:\n{page_num}\n\n"
                f"Chunk:\n{chunk_id}\n\n"
                f"Text:\n{chunk.strip()}"
            )
        contexts_block = "\n\n---\n\n".join(contexts_block_list)

        user_prompt = (
            f"{contexts_block}\n\n"
            f"Question:\n{question}"
        )

        # 4. Token Budget estimation (Calculated word length of combined prompts)
        combined_words = len(system_prompt.split()) + len(user_prompt.split())
        words_budget = max(50, token_budget - combined_words)

        return PromptPackage(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            token_budget=words_budget,
            metadata={
                "empty_retrieval": False,
                "total_retrieved_chunks": len(retrieved_context.retrieved_chunks),
                "headings_count": len(retrieved_context.headings),
                "pages_count": len(retrieved_context.pages)
            }
        )

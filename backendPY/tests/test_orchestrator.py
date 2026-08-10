import os
import uuid
import unittest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from models.models import Document, Page, Chunk, Embedding
from services.orchestrator import DocumentOrchestrator
from services.orchestrator import (
    OCRServiceAdapter, ChunkingServiceAdapter, EmbeddingServiceAdapter,
    ExtractionServiceAdapter, ConflictServiceAdapter, ClarificationServiceAdapter
)

class TestOrchestratorPipeline(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Create a mock text file
        self.test_file_path = "mock_test_doc.txt"
        with open(self.test_file_path, "w") as f:
            f.write("Jane Doe has atrial fibrillation. Normal ECG.")

        # Create mock db session - using MagicMock so sync methods (add, flush) return sync values,
        # while explicitly setting AsyncMock for database operations.
        self.db = MagicMock()
        self.db.commit = AsyncMock()
        self.db.rollback = AsyncMock()
        self.db.refresh = AsyncMock()
        self.db.flush = AsyncMock()
        
        # Setup document mock
        self.doc_id = uuid.uuid4()
        self.project_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.document = Document(
            id=self.doc_id,
            project_id=self.project_id,
            user_id=self.user_id,
            file_name="mock_test_doc.txt",
            file_type="text",
            file_path=self.test_file_path,
            status="uploaded"
        )

        # Dynamic handler to mock query execution text-by-text
        async def mock_execute(query, *args, **kwargs):
            query_str = str(query).lower()
            mock_res = MagicMock()
            
            if "from documents" in query_str:
                mock_res.scalar_one_or_none.return_value = self.document
            elif "from document_results" in query_str:
                mock_res.scalar_one_or_none.return_value = None
            else:
                # Return empty page/chunk/fact lists
                mock_res.scalars.return_value.all.return_value = []
                mock_res.scalar_one_or_none.return_value = None
            return mock_res

        self.db.execute = AsyncMock(side_effect=mock_execute)

    async def asyncTearDown(self):
        if os.path.exists(self.test_file_path):
            os.remove(self.test_file_path)

    async def test_full_orchestration_pipeline_with_mocks(self):
        # 1. Setup mock service adapters
        ocr_service = MagicMock()
        chunking_service = MagicMock()
        embedding_service = AsyncMock()
        extraction_service = AsyncMock()
        conflict_service = AsyncMock()
        clarification_service = AsyncMock()

        # Mock adapter return values
        ocr_service.extract_pages.return_value = [
            {"page_number": 1, "text": "Jane Doe has atrial fibrillation. Normal ECG.", "image_path": "/files/mock.png"}
        ]
        chunking_service.chunk_page.return_value = ["Jane Doe has atrial fibrillation.", "Normal ECG."]
        embedding_service.generate_and_save_embeddings.return_value = None
        extraction_service.extract_knowledge.return_value = None
        conflict_service.detect_conflicts.return_value = 0
        clarification_service.check_and_trigger.return_value = 0

        # 2. Instantiate Orchestrator
        orchestrator = DocumentOrchestrator(
            ocr_service=ocr_service,
            chunking_service=chunking_service,
            embedding_service=embedding_service,
            extraction_service=extraction_service,
            conflict_service=conflict_service,
            clarification_service=clarification_service
        )

        # 3. Execute
        await orchestrator.process_document(self.db, self.doc_id, self.test_file_path)

        # 4. Assert sequence of operations
        ocr_service.extract_pages.assert_called_once_with(self.test_file_path)
        conflict_service.detect_conflicts.assert_called_once_with(self.db, self.project_id, self.user_id)
        clarification_service.check_and_trigger.assert_called_once_with(self.db, self.project_id, self.user_id, self.doc_id)

        # Assert document status transitioned to completed
        self.assertEqual(self.document.status, "completed")
        self.assertGreaterEqual(self.db.commit.call_count, 1)

if __name__ == "__main__":
    unittest.main()

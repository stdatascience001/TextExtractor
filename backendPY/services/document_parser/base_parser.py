import abc
from services.document_parser.models import ParsedDocumentWrapper

class BaseDocumentParser(abc.ABC):
    @abc.abstractmethod
    def parse(self, file_path: str, document_id: str) -> ParsedDocumentWrapper:
        """Parses a document file and returns a structured hierarchical document model."""
        pass

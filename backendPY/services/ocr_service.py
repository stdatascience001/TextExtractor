import os
from typing import List, Dict

# We import PaddleOCR inside the class property getter to avoid importing it immediately
# if the service module is loaded before the model dependencies are fully initialized.
# This prevents premature initialization errors.

class PaddleOCRService:
    _instance = None
    _ocr_model = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(PaddleOCRService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    @property
    def model(self):
        if self._ocr_model is None:
            print("Initializing PaddleOCR model (CPU)...")
            from paddleocr import PaddleOCR, logger
            import logging
            # Suppress verbose paddle logging
            logger.setLevel(logging.WARNING)
            # Initialize PaddleOCR once. GPU is disabled.
            self._ocr_model = PaddleOCR(
                lang='en',
                device='cpu',
                enable_mkldnn=True,
                ocr_version='PP-OCRv4',
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                cpu_threads=4
            )
        return self._ocr_model

    def extract_ocr_blocks(self, image_path: str) -> List[Dict]:
        """
        Runs PaddleOCR on the image and returns structured blocks:
        [
            {
                "text": "Extracted Text",
                "bbox": [xmin, ymin, xmax, ymax],
                "confidence": 0.95
            }
        ]
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        # In PaddleOCR 3.x, predict() returns a list of OCRResult objects
        # We disable document classification, unwarping, and text orientation classification to dramatically speed up CPU inference.
        results = self.model.predict(
            image_path,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False
        )
        
        blocks = []
        if not results:
            return blocks

        first = results[0]
        texts = first.get("rec_texts", [])
        scores = first.get("rec_scores", [])
        boxes = first.get("rec_boxes", [])

        for text, score, box in zip(texts, scores, boxes):
            bbox = [int(val) for val in box]
            blocks.append({
                "text": text.strip(),
                "bbox": bbox,
                "confidence": round(float(score), 4)
            })
            
        return blocks

    def extract_text_from_image(self, image_path: str) -> str:
        """
        Helper method to extract plain text string (maintaining backwards compatibility).
        """
        blocks = self.extract_ocr_blocks(image_path)
        return " ".join([b["text"] for b in blocks]).strip()

# Create a single global instance for imports
ocr_service = PaddleOCRService()

def extract_ocr_blocks(image_path: str) -> List[Dict]:
    return ocr_service.extract_ocr_blocks(image_path)

def extract_text_from_image(image_path: str) -> str:
    return ocr_service.extract_text_from_image(image_path)

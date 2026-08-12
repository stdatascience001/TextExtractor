import re
import urllib.request
import urllib.error
import zipfile
import io
from core.logging import logger

def extract_spreadsheet_id(url: str) -> str:
    """Extract Google spreadsheet ID from URL using regex."""
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    if not match:
        raise ValueError("Invalid Google Sheets URL. Could not extract spreadsheet ID.")
    return match.group(1)

class GoogleSheetsService:
    @staticmethod
    def fetch_public_sheet_as_xlsx(url: str) -> bytes:
        """
        Extracts spreadsheet ID and downloads public Google Sheet as XLSX bytes.
        Validates that it is a valid Excel zip structure.
        """
        spreadsheet_id = extract_spreadsheet_id(url)
        export_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=xlsx"
        
        logger.info(f"[GoogleSheetsService] Downloading spreadsheet {spreadsheet_id} as XLSX...")
        
        req = urllib.request.Request(
            export_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                data = response.read()
        except urllib.error.HTTPError as http_err:
            logger.error(f"[GoogleSheetsService] HTTP Error during download: {str(http_err)}")
            if http_err.code in (401, 403):
                raise ValueError("Failed to import: The Google Sheet is private or restricted. Please configure it to 'Anyone with the link can view' before importing.")
            raise ValueError(f"Failed to connect to Google Sheets: {str(http_err)}")
        except Exception as e:
            logger.error(f"[GoogleSheetsService] Download failed: {str(e)}")
            raise ValueError(f"Failed to connect to Google Sheets: {str(e)}")
            
        # Validate that the downloaded file is a valid zip archive (since .xlsx is a zip format)
        # Private sheets will return HTML sign-in pages instead of zip binaries.
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                # Valid zip, return bytes
                return data
        except zipfile.BadZipFile:
            logger.error("[GoogleSheetsService] Downloaded data is not a valid zip structure. Sheet is likely private.")
            raise ValueError("Failed to import. The Google Sheet must be publicly shared ('Anyone with the link can view').")

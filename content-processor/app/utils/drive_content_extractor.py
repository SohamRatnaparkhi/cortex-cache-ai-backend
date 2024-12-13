import os
from typing import Optional, Tuple

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.schemas.Metadata import GDriveFileType

if os.path.exists('.env'):
    load_dotenv()

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')


class GDriveProcessor:
    def __init__(self, file_id: str, access_token: str, refresh_token: Optional[str] = None):
        self.file_id = file_id
        self.credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            token_uri="https://oauth2.googleapis.com/token",
        )
        self.service = build('drive', 'v3', credentials=self.credentials)

    def get_file_type(self) -> Tuple[GDriveFileType, dict]:
        """Get file type and metadata from Drive API"""
        file = self.service.files().get(
            fileId=self.file_id,
            fields='mimeType,name'
        ).execute()

        mime_type = file['mimeType']

        if mime_type == GDriveFileType.GDOC.value:
            return GDriveFileType.GDOC, file
        elif mime_type == GDriveFileType.GSHEET.value:
            return GDriveFileType.GSHEET, file
        elif mime_type == GDriveFileType.GSLIDE.value:
            return GDriveFileType.GSLIDE, file
        elif mime_type.startswith('image/'):
            return GDriveFileType.IMAGE, file
        elif mime_type.startswith('audio/'):
            return GDriveFileType.AUDIO, file
        elif mime_type.startswith('video/'):
            return GDriveFileType.VIDEO, file
        elif mime_type == 'application/pdf':
            return GDriveFileType.PDF, file
        else:
            return GDriveFileType.UNKNOWN, file

    def extract_doc_content(self) -> str:
        """Extract content from Google Doc"""
        docs_service = build('docs', 'v1', credentials=self.credentials)
        document = docs_service.documents().get(documentId=self.file_id).execute()
        content = []

        for elem in document.get('body').get('content'):
            if 'paragraph' in elem:
                for para_elem in elem['paragraph']['elements']:
                    if 'textRun' in para_elem:
                        content.append(para_elem['textRun']['content'])

        return '\n'.join(content)

    def extract_sheet_content(self) -> str:
        """Extract content from Google Sheet"""
        sheets_service = build('sheets', 'v4', credentials=self.credentials)
        spreadsheet = sheets_service.spreadsheets().get(
            spreadsheetId=self.file_id
        ).execute()

        content = []

        for sheet in spreadsheet['sheets']:
            sheet_name = sheet['properties']['title']
            result = sheets_service.spreadsheets().values().get(
                spreadsheetId=self.file_id,
                range=sheet_name
            ).execute()

            rows = result.get('values', [])
            sheet_content = []
            for row in rows:
                sheet_content.append(' | '.join(str(cell) for cell in row))

            content.append(f"Sheet: {sheet_name}\n" + '\n'.join(sheet_content))

        return '\n\n'.join(content)

    def extract_slide_content(self) -> str:
        """Extract content from Google Slides"""
        slides_service = build('slides', 'v1', credentials=self.credentials)
        presentation = slides_service.presentations().get(
            presentationId=self.file_id
        ).execute()

        content = []
        slide_number = 1

        for slide in presentation.get('slides', []):
            slide_content = []
            slide_content.append(f"Slide {slide_number}:")

            for element in slide.get('pageElements', []):
                if 'shape' in element and 'text' in element['shape']:
                    for textElement in element['shape']['text'].get('textElements', []):
                        if 'textRun' in textElement:
                            slide_content.append(
                                textElement['textRun']['content'])

            content.append('\n'.join(slide_content))
            slide_number += 1

        return '\n\n'.join(content)

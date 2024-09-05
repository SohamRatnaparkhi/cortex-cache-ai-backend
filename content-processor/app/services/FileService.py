from app.core.agents.MediaAgent import File_PDFAgent


def extract_text_from_pdf(s3_url: str) -> str:
    agent = File_PDFAgent(s3_url)
    return agent.process_media()
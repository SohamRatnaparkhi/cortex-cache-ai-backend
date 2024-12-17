from app.core.agents.MediaAgent import ImageAgent
from app.schemas.Metadata import ImageSpecificMd, Metadata


async def get_image_transcript(s3_bucket_key, metadata: Metadata[ImageSpecificMd]) -> dict:
    image_agent = ImageAgent(s3_media_key=s3_bucket_key, md=metadata)
    return await image_agent.process_media()

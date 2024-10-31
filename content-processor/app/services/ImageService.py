from app.core.agents.MediaAgent import ImageAgent
from app.schemas.Metadata import ImageSpecificMd, Metadata


def get_image_transcript(s3_bucket_key, metadata: Metadata[ImageSpecificMd]) -> dict:
    print('get_image_transcript')
    image_agent = ImageAgent(s3_media_key=s3_bucket_key, md=metadata)
    return image_agent.process_media()

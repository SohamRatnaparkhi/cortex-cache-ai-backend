from app.core.agents.MediaAgent import ImageAgent


def get_image_transcript(s3_bucket_key):
    image_agent = ImageAgent(s3_media_key=s3_bucket_key)
    return image_agent.process_media()

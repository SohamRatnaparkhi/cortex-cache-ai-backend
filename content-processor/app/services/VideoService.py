from app.core.agents.MediaAgent import VideoAgent


def get_video_transcript(s3_bucket_key):
    video_agent = VideoAgent(s3_media_key=s3_bucket_key)
    return video_agent.process_media()
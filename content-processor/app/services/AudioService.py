from app.core.agents.MediaAgent import AudioAgent


def get_audio_transcript(s3_bucket_key):
    audio_agent = AudioAgent(s3_media_key=s3_bucket_key)
    return audio_agent.process_media()
# import asyncio
# import threading

# from aiokafka import AIOKafkaConsumer


# async def consume_messages(group_id: str):
#     loop = asyncio.get_event_loop()
#     consumer = AIOKafkaConsumer(
#         'code',
#         'content',
#         'text',
#         loop=loop,
#         bootstrap_servers='localhost:9092',
#         group_id=group_id
#     )
#     await consumer.start()
#     try:
#         async for msg in consumer:
#             print(f"Consumed message by {group_id}: {msg.value.decode('utf-8')}")
#     finally:
#         await consumer.stop()

import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer

from app.core.agents.LinkAgents import GitAgent, YoutubeAgent
from app.schemas.Metadata import GitSpecificMd, Metadata, YouTubeSpecificMd

logger = logging.getLogger(__name__)

consumer_tasks = {}


async def kafka_consumer_task(group_id: str):
    logger.info(f"Kafka consumer {group_id} started")
    while True:
        try:
            consumer = AIOKafkaConsumer(
                'code', 'media', 'text',
                bootstrap_servers='localhost:9092',
                group_id=group_id,
                session_timeout_ms=30000,
                heartbeat_interval_ms=3000,
                max_poll_interval_ms=300000,
                enable_auto_commit=False,
                # auto_offset_reset='earliest'
            )
            await consumer.start()
            try:
                async for msg in consumer:
                    print(f"Consumed message by {group_id}: {msg.value.decode('utf-8')}")
                    logger.info(
                        f"Consumed message by {group_id}: {msg.value.decode('utf-8')}")
                    # Process the message here
                    handle_message(msg.value.decode('utf-8'))
                    await consumer.commit()
            finally:
                await consumer.stop()
        except Exception as e:
            logger.error(f"Unexpected error in consumer {group_id}: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error details: {e.args}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

        logger.info(
            f"Consumer {group_id} disconnected. Reconnecting in 5 seconds...")
        await asyncio.sleep(5)

def handle_message(msg: str):
    json_msg = json.loads(msg)
    type = json_msg.get("type")
    if type == "code":
        metadata_dict = json_msg.get("metadata")
        repo_link = json_msg.get("repo_url")
        # Convert the metadata dictionary to a Metadata object
        specific_desc = GitSpecificMd(**metadata_dict.pop("specific_desc"))
        metadata = Metadata(**metadata_dict, specific_desc=specific_desc)
        
        git_agent = GitAgent(repo_link, metadata)
        git_agent.process_media()
        print("git processed")
    elif type == "youtube":
        video_url = json_msg.get("video_url")
        metadata = json_msg.get("metadata")
        # Convert the metadata dictionary to a Metadata object
        specific_desc = YouTubeSpecificMd(**metadata.pop("specific_desc"))
        metadata = Metadata(**metadata, specific_desc=specific_desc)
        youtube_agent = YoutubeAgent(video_url, metadata)
        youtube_agent.process_media()
        print("youtube processed")
        # save to database
        pass
    elif type == "text":
        # save to database
        pass
    else:
        print("unknown type")
        pass

def convert_str_to_dict(metadata: str):
    return json.loads(metadata)
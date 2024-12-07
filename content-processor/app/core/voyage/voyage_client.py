import os
import time

import voyageai
from dotenv import load_dotenv

from app.utils.app_logger_config import logger

if (os.path.exists('.env')):
    load_dotenv()

vo = voyageai.Client()

batch_size = 128


def get_embeddings(documents: list[str], is_code=False) -> list:
    try:
        model = "voyage-3" if not is_code else "voyage-3-code"
        embeddings = []
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            embeddings.extend(vo.embed(batch, model=model).embeddings)

            if (len(documents) / batch_size) > 4:
                time.sleep(1)
        return embeddings
    except Exception as e:
        logger.error(f"Error getting embeddings: {e}")
        return []

import os
import random

import requests
from dotenv import load_dotenv

load_dotenv()

total_keys = os.getenv("TOTAL_JINA_AI_API_KEYS")
start = 1

all_api_keys = []

while start <= int(total_keys):
    all_api_keys.append(os.getenv(f"JINA_API_KEY_{start}"))
    start += 1


def randomly_choose_one_key_with_equal_prob():
    # print(all_api_keys)
    key = random.choice(all_api_keys)
    if key is None:
        key = os.getenv("JINA_API_KEY_1")
    return key


class JinaAIClient():
    def __init__(self, base_url, isReader=False):
        self.base_url = base_url
        self.isReader = isReader

    def get_random_header(self):
        key = randomly_choose_one_key_with_equal_prob()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}"
        }
        if self.isReader:
            headers["Accept"] = "application/json"
            headers.pop("Content-Type")
        return headers

    def get(self, endpoint=''):
        headers = self.get_random_header()
        # print(self.isReader)
        # print(headers)
        response = requests.get(self.base_url + endpoint, headers=headers)
        # print(response.json())
        return response.json()

    def post(self, data, endpoint=''):
        headers = self.get_random_header()
        # print(headers)
        response = requests.post(
            self.base_url + endpoint, headers=headers, json=data)
        return response.json()

    def delete(self, endpoint=''):
        headers = self.get_random_header()
        response = requests.delete(self.base_url + endpoint, headers=headers)
        return response.json()

    def put(self, data, endpoint=''):
        headers = self.get_random_header()
        response = requests.put(self.base_url + endpoint,
                                headers=headers, json=data)
        return response.json()

import os
import random

import aiohttp
import requests
from dotenv import load_dotenv

from app.utils.proxy import get_random_proxy

if os.path.exists('.env'):
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
        self.retry = 0

    def get_random_header(self):
        key = randomly_choose_one_key_with_equal_prob()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}"
        }
        if self.isReader:
            headers["Accept"] = "application/json"
            headers.pop("Content-Type")
            headers["X-Remove-Selector"] = "img, a"
            headers["X-Timeout"] = "60"
            # headers["X-Proxy-Url"] = get_random_proxy(
            #     index=self.retry)
        return headers

    async def get(self, endpoint=''):
        headers = self.get_random_header()
        async with aiohttp.ClientSession() as session:
            try:
                print("Headers: ", headers)
                # if self.retry == 10:
                #     headers.pop("X-Proxy-Url")
                proxyIp = get_random_proxy(app='yt')
                async with session.get(self.base_url + endpoint, headers=headers, proxy=proxyIp) as response:
                    return await response.json()
            except aiohttp.ClientError as e:
                # Handle network-related errors
                raise Exception(f"Network error occurred: {str(e)}")
            except ValueError as e:
                # Handle JSON decode errors
                raise Exception(f"JSON decode error: {str(e)}")

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

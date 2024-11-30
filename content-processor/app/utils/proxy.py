import random

username = 'spnaa652yk'
password = '9m6lh_gSjl5qqV1ORg'

proxies = [
    f'http://{username}:{password}@gate.smartproxy.com:10001'
]


def get_random_proxy():
    return random.choice(proxies)

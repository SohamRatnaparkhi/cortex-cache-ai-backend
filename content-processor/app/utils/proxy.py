import random

username = 'spnaa652yk'
password = '9m6lh_gSjl5qqV1ORg'
ports = [10001, 10002, 10003, 10004, 10005, 10006, 10007, 10008, 10009, 10010]

proxies = [
    f'http://{username}:{password}@gate.smartproxy.com:{port}' for port in ports
]


def get_random_proxy():
    return random.choice(proxies)

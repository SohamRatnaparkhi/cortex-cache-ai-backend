import asyncio

from deep_translator import GoogleTranslator

from app.utils.proxy import get_random_proxy

proxyIp = get_random_proxy(app='yt')

proxy = {
    'http': proxyIp,
    'https': proxyIp
}


client = GoogleTranslator(source='auto', target='en', proxies=proxy)


async def translate_text(text: str) -> str:
    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.translate(text=text)
        )
        # print(response)
        return response
    except Exception as e:
        print(e)
        return ""

import asyncio
import ssl

import aiohttp
import certifi


async def main():
    # resolve certificate-verification problems when the Python installation 
    # does not correctly locate the operating system’s CA certificates.
    ssl_context = ssl.create_default_context(cafile=certifi.where())

    connector = aiohttp.TCPConnector(ssl=ssl_context)

    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get("https://api.tavily.com") as response:
            print(response.status)


asyncio.run(main())

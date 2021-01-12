import re
import os
import sys
import asyncio
import aiohttp
from urllib.parse import quote
from aiohttp import TCPConnector

g_url = 'http://java.52emu.cn/'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
}

g_task_num = 0
g_pattern = r"<a href='(\?nsort=.*?)'>(.*?)</a>"
g_sub_pattern = r"<a href='(xiangqing\.php\?id=\d{1,5})'>.*?</a>"
g_download_pattern = r"<a href='(\./jargame/\d/.*?)'>.*?</a>"
g_store_path = "j2me_game"
has_task = True

async def download(sem, download_url, filepath, session):
    global g_task_num
    global has_task
    g_task_num += 1
    print("开始下载" + str(filepath) + ", 当前有" + str(g_task_num) + "个下载任务")
    async with sem:
        try:
            async with session.get(download_url, headers=headers) as resp2:
                if not resp2.status == 200:
                    raise ValueError("")
                try:
                    content = await resp2.read()
                except Exception as e:
                    print(filepath + "下载错误, 5秒后会从新开始下载")
                    g_task_num -= 1
                    await asyncio.sleep(5)
                    asyncio.ensure_future(download(sem, download_url, filepath, session))
                    return
                with open(filepath, 'wb') as fp:
                    fp.write(content)
            g_task_num -= 1
            print(filepath + "下载完成" + ", 当前有" + str(g_task_num) + "个下载任务")
            if g_task_num == 0:
                has_task = False
        except Exception as e:
            print("请求页面错误, 5秒后会重新请求")
            g_task_num -= 1
            await asyncio.sleep(5)
            asyncio.ensure_future(download(sem, download_url, filepath, session))

async def fetch_one(sem, url, path, session):
    async with sem:
        try:
            async with session.get(url, headers=headers) as resp:
                if not resp.status == 200:
                    raise ValueError("")
                try:
                    text = await resp.text()
                except Exception as e:
                    print('获得页面内容失败, 5秒后会重新请求')
                    await asyncio.sleep(5)
                    asyncio.ensure_future(fetch_one(sem, url, path, session))
                    return
                ret = re.findall(g_download_pattern, text, re.S)
                if len(ret) > 0:
                    ret = ret[0]
                    game_name = ret.split('/')
                    if len(game_name) > 0:
                        game_name = game_name[len(game_name) - 1]
                    else:
                        return
                else:
                    return
                filepath = os.path.join(path, game_name)
                download_url = quote(g_url + ret, safe='/:?=&', encoding='utf-8')
                asyncio.ensure_future(download(sem, download_url, filepath, session))
        except Exception as e:
            print("请求页面错误, 5秒后会重新请求")
            await asyncio.sleep(5)
            asyncio.ensure_future(fetch_one(sem, url, path, session))

async def parse_one(sem, url, path, session):
    async with sem:
        try:
            async with session.get(url, headers=headers) as resp:
                if not resp.status == 200:
                    raise ValueError("")
                try:
                    text = await resp.text()
                except Exception as e:
                    print('获得页面内容失败, 5秒后会重新请求')
                    await asyncio.sleep(5)
                    asyncio.ensure_future(parse_one(sem, url, path, session))
                    return
                ret = re.findall(g_sub_pattern, text, re.S)
                for sub_download_url in ret:
                    d_url = g_url + sub_download_url
                    asyncio.ensure_future(fetch_one(sem, d_url, path, session))
        except Exception as e:
            print("请求页面错误, 5秒后会重新请求")
            await asyncio.sleep(5)
            asyncio.ensure_future(parse_one(sem, url, path, session))

async def start(sem, session):
    async with session.get(g_url, headers=headers) as resp:
        if not resp.status == 200:
            sys.exit()
        text = await resp.text()
        ret = re.findall(g_pattern, text, re.S)
        for enter in ret:
            sub_url, sort_name = enter
            path = os.path.join(g_store_path, sort_name)
            if not os.path.exists(path):
                os.makedirs(path)
            url = g_url + sub_url
            asyncio.ensure_future(parse_one(sem, url, path, session))

async def main(max):
    sem = asyncio.Semaphore(max)
    async with sem:
        async with aiohttp.ClientSession(connector=TCPConnector(limit=400, verify_ssl=False)) as session:
            await start(sem, session)
            while has_task:
                await asyncio.sleep(3)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    asyncio.ensure_future(main(300))
    loop.run_forever()
    print("所有都下载完毕")

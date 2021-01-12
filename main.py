import re
import os
import sys
import asyncio
import aiohttp
from urllib.parse import quote
from aiohttp import TCPConnector

g_url = 'http://java.52emu.cn/'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
    'cookie': 'UM_distinctid=176e53813982f9-0e755bc35327fd-5c19341b-100200-176e5381399719; CNZZDATA5288474=cnzz_eid%3D1306601004-1610163247-https%253A%252F%252Fpan.lanzou.com%252F%26ntime%3D1610281144; CNZZDATA1253610888=2054105360-1610162029-https%253A%252F%252Fpan.lanzou.com%252F%7C1610281154; CNZZDATA909149=cnzz_eid%3D413988840-1610280198-https%253A%252F%252Fpan.lanzou.com%252F%26ntime%3D1610280198',
    ':authority': 'pan.lanzou.com',
    ':method': 'GET',
    ':scheme': 'https',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'referer': 'https://pan.lanzou.com/tp//i05edzc'
}

g_task_num = 0
g_pattern = r"<a href='(\?nsort=.*?)'>(.*?)</a>"
g_sub_pattern = r"<a href='(xiangqing\.php\?id=\d{1,5})'>.*?</a>"
g_download_pattern = r"<a href='(https://pan.lanzou.com/tp//.*?)'>网盘下载</a>"
g_store_path = "j2me_game"
has_task = True

async def download(sem, download_url, filepath, session):
    global g_task_num
    global has_task
    g_task_num += 1
    print("开始下载" + str(filepath) + ", 当前有" + str(g_task_num) + "个下载任务")

    g_task_num -= 1
    print(filepath + "下载完成" + ", 当前有" + str(g_task_num) + "个下载任务")
    if g_task_num == 0:
        has_task = False

async def parse_lzy(sem, download_url, filepath, session):
    async with sem:
        try:
            async with session.get(download_url, headers=headers) as resp2:
                if not resp2.status == 200:
                    raise ValueError("")
                try:
                    content = await resp2.read()
                    print(content)
                except Exception as e:
                    print('获得页面内容失败, 5秒后会重新请求')
                    await asyncio.sleep(5)
                    asyncio.ensure_future(parse_lzy(sem, download_url, filepath, session))
                    return
        except Exception as e:
            print("请求页面" + str(download_url) + "错误, 5秒后会重新请求")
            await asyncio.sleep(5)
            asyncio.ensure_future(parse_lzy(sem, download_url, filepath, session))

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
                        return None
                else:
                    return None
                filepath = os.path.join(path, game_name)
                download_url = ret
                # print(download_url)
                asyncio.ensure_future(parse_lzy(sem, download_url, filepath, session))
        except Exception as e:
            print("请求页面" + str(url) + "错误, 5秒后会重新请求")
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
                    break
        except Exception as e:
            print("请求页面" + str(url) + "错误, 5秒后会重新请求")
            await asyncio.sleep(5)
            asyncio.ensure_future(parse_one(sem, url, path, session))

async def start(sem, session):
    async with session.get(g_url, headers=headers) as resp:
        if not resp.status == 200:
            return
        text = await resp.text()
        ret = re.findall(g_pattern, text, re.S)
        for enter in ret:
            sub_url, sort_name = enter
            path = os.path.join(g_store_path, sort_name)
            if not os.path.exists(path):
                os.makedirs(path)
            url = g_url + sub_url
            asyncio.ensure_future(parse_one(sem, url, path, session))
            break

async def main(max):
    sem = asyncio.Semaphore(max)
    async with sem:
        async with aiohttp.ClientSession(connector=TCPConnector(limit=400, verify_ssl=False)) as session:
            await start(sem, session)
            while has_task:
                await asyncio.sleep(2)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    asyncio.ensure_future(main(300))
    loop.run_forever()
    print("所有都下载完毕")

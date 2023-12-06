import asyncio, aiohttp, aiofiles, re, json
from tqdm.asyncio import tqdm
from datetime import datetime

class downloader:
    async def download(url: str, si = None, nsi = None, maxsize: int = None):
        headers = {
            'authority': 'm.vk.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.8',
            'cache-control': 'max-age=0',
            'referer': 'https://m.vk.com/',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36',
        }
        if not si and not nsi:
            from env import sid, nsid
            si = sid
            nsi = nsid
        cookies = {
            'remixmdevice': '453/685/2.0000000298023224/!!!!!!!!!!!-/400',
            'remixnsid': nsid,
            'remixsid': sid,
        }
        origurl = url
        if 'wall' in url:
            origurl, author = await downloader.exracturl(url, headers, cookies)
        if "video" in origurl:
            thejson, author = await downloader.extractjson(origurl, headers, cookies)
            videos = thejson[5]["apiPrefetchCache"][0]["response"]["items"][0]["files"]
            videoinfo = {}
            async with aiohttp.ClientSession() as session:
                for key, value in videos.items():
                    if key == "failover_host":
                        continue
                    async with session.get(value, headers=headers, cookies=cookies) as r:
                        videoinfo[key] = r.headers.get("content-length")
            videoinfosort = sorted(videoinfo.items(), key=lambda x: int(x[1]) if x else None, reverse=True)
            videoinfo = {}
            for formt, size in videoinfosort:
                videoinfo[formt] = size

            for key, value in videoinfo.items():
                if maxsize and maxsize > value/(1024*1024):
                    continue
            
                filename = f"{author}-{round(datetime.now().timestamp())}.mp4"
                await downloader.downloader(videos.get(key), filename, headers, cookies)
                break
            return filename
                
        elif "wall" in origurl:
            image = await downloader.extractimage(origurl, headers, cookies)

            filename = f"{author}-{round(datetime.now().timestamp())}.jpg"
            await downloader.downloader(image, filename, headers, cookies)
            return filename
        elif "album" in origurl:
            images, author = await downloader.extractimages(origurl, headers, cookies)
            filenames = []
            for index, image in enumerate(images):
                filename = f"{author}-{round(datetime.now().timestamp())}-{index}.jpg"
                filenames.append(filename)
                await downloader.downloader(image, filename, headers, cookies)
            return filenames
        print(author)
    async def downloader(url, filename, headers, cookies):
        async with aiofiles.open(filename, 'wb') as f1:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, cookies=cookies) as r:
                    progress =tqdm(total=int(r.headers.get('content-length')), unit="iB", unit_scale=True)
                    while True:
                        chunk = await r.content.read(1024)
                        if not chunk:
                            break
                        await f1.write(chunk)
                        progress.update(len(chunk))
                    progress.close()
    async def extractimage(url, headers, cookies):
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, cookies=cookies) as r:
                pattern = r'background-image: url\((.*?)\);\"  class=\"thumb_map_img thumb_map_img_as_div\"'
                matches = None

                while True:
                    chunk = await r.content.read(1024 * 10)
                    if not chunk:
                        break
                    decoded = chunk.decode("utf-8", errors="replace")


                    matches = re.findall(pattern, decoded)
                    if matches:
                        matches = matches[0]
                        break
        return matches
    async def extractimages(url, headers, cookies):
        images = []
        pattern = r'data-src_big=\"(.*?)\"'
        pattern2 = r'<a href=\"/(.*?)\" class=\"PhotosPhotoItem al_photo\"'
        author = None
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, cookies=cookies) as r:
                while True:
                    chunk = await r.content.read(1024*20)
                    if not chunk:
                        break
                    decoded = chunk.decode("utf-8", errors="replace")

                    matches = re.findall(pattern, decoded)
                    if matches:
                        for match in matches:
                            images.append(match)
                    if not author:
                        matches2 = re.findall(pattern2, decoded)
                        if matches2:
                            url = "https://m.vk.com/" + matches2[0]
                            async with session.get(url, headers=headers, cookies=cookies) as r2:
                                pattern3 = r'<a class=\"AlbumInfoRow__avatar\" href=\"/(.*?)\"'
                                while True:
                                    chunk = await r2.content.read(1024*10)
                                    if not chunk:
                                        break
                                    mat = re.findall(pattern3, chunk.decode("utf-8"))
                                    if mat:
                                        break
                            author = mat[0]

        return images, author
    async def exracturl(url: str, headers, cookies):
        """extracts original url for post"""


        url = url.replace("https://vk.com", "https://m.vk.com")
        pattern = r'property=\"og:url\" content=\"(https://vk\.com/(?:.*?))\"'
        pattern2 = r'<title>Post from (?:.*?) \| (.*?)</title>'
        matches = False
        matches2 = False
        async with aiohttp.ClientSession() as session:
            async with session.get(url, cookies=cookies, headers=headers) as r:
                while True:
                    chunk = await r.content.read(1024*10)
                    if not chunk:
                        break
                    decoded = chunk.decode("utf-8", errors="replace")
                    if not matches:
                        matches = re.findall(pattern, decoded)
                        if matches:
                            matches = matches[0]
                    if not matches2:
                        matches2 = re.findall(pattern2, decoded)
                        if matches2:
                            matches2 = matches2[0]
                    if matches and matches2:
                        break
        return matches, matches2
    async def extractjson(url, headers, cookies):
        pattern = r'window\.extend\(window\.lang,({\"global_date_l\":(?:.*?))\;vk\.started=Date\.now\(\);onlo'
        pattern2 = r'\"md_author\":\"(.*?)\"'
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, cookies=cookies) as r:
                rtext = await r.text(encoding="utf-8")
        matches = re.findall(pattern, rtext)
        if matches:
            found: str = "[" + matches[0].replace(");extend(window.cur, ", ",").rstrip(')') + "]"
        else:
            print("no matches")
            return False
        parsed = json.loads(found)
        author = re.findall(pattern2, rtext)[0]
        return parsed, author
if __name__ == "__main__":
    # result = asyncio.run(downloader.download("https://vk.com/album-43608823_173209811"))
    # result = asyncio.run(downloader.download("https://vk.com/video-191706891_456256368"))
    # result = asyncio.run(downloader.download("https://vk.com/wall-218166128_2528"))
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("link", type=str, help="link to vk post/линк до посту")
    parser.add_argument("-m", type=int, help="max size of video in mb/максимальный размер видео в мб")
    args = parser.parse_args()
    asyncio.run(downloader.download(args.link, args.m))
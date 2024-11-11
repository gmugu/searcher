#!/usr/bin/python3

import traceback
import aiohttp
from aiohttp import web
import asyncio
import time
import hashlib
import json
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, quote

PORT_NUMBER = 9094

G_LAST_LOGIN_TIME_189 = 0

URL_HOST = {
    "139": "http://www.91panta.cn",
    "189": "https://www.leijing.xyz",
    "xiaoya": "https://xiaoya.zaob.in",
    "zhaoziyuan": "https://zhaoziyuan1.cc",
    "pansearch": "https://www.pansearch.me",
    "kf": "https://kuafuzys.com",
}


class ClientSessionSingleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.session_139 = aiohttp.ClientSession()
            cls._instance.session_189 = aiohttp.ClientSession()
            cls._instance.session_kf = aiohttp.ClientSession()
            cls._instance.session_kf.cookie_jar.update_cookies({
                'bbs_sid': '710u7bhv6h5hpu5g38jm09h6et',
                'bbs_token': 'rlxsdNkqVXPnAi2XwMMkPnSgR3dXVPxD_2BIhEvABzvWDNsh_2BaDJikL0r1CG7tTZHt6UiYz7N7Nt1rPTrih5IgSA_3D_3D',
            })
        return cls._instance


async def check_should_login():
    if time.time() - G_LAST_LOGIN_TIME_189 > 1 * 24 * 60 * 60:
        await login_189(ClientSessionSingleton().session_189, "mugu", "88888888")


async def search_pansearch(keyword, limit=10, offset=0, pan=None):
    url = f"{URL_HOST['pansearch']}/api/search?keyword={keyword}&limit={limit}&offset={offset}"
    if pan != None:
        url = url + "&pan={pan}"

    headers = {
        "Host": "www.pansearch.me",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh-Hans;q=0.9",
        "Connection": "keep-alive",
        "Accept-Encoding": "gzip, deflate",
        "User-Agent": "PanSearch/2 CFNetwork/1494.0.7 Darwin/23.4.0",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            return await response.json()


async def search_xiaoya(keyword, type="all"):
    url = f"{URL_HOST['xiaoya']}/search?box={keyword}&type={type}&url="

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")
            body_divs = soup.body.find_all("div")
            for div in body_divs:
                ul = div.find("ul")
                if ul:
                    result_list = []
                    for a in ul.find_all("a"):
                        if "href" in a.attrs:
                            result_list.append(
                                {
                                    "title": a.text,
                                    "href": URL_HOST["xiaoya"] + a["href"],
                                }
                            )

                    return {"result_list": result_list, "count": len(result_list)}

            raise Exception("html文档解析失败")

async def search_kf(keyword):
    kwEncode = quote(keyword).replace('%', '_')
    url = f"{URL_HOST['kf']}/search-{kwEncode}-1-0-1.htm"
    async with ClientSessionSingleton().session_kf.get(url) as response:
        html = await response.text()
        soup = BeautifulSoup(html, "html.parser")

        result_list = []
        lis = soup.find_all('li', class_=["media", "thread", "tap"])
        for li in lis:
            ret = {}
            ret['id'] = li['data-tid']
            ret['href'] = f"{URL_HOST['kf']}/{li['data-href']}"
            # ret['avatarPath'] = f"{URL_HOST['kf']}/{li.find('img')['src']}"
            # ret['nickname'] = li.find('span', class_=["username", "text-muted", "mr-1", "hidden-sm"]).text.split('•')[0].strip()
            
            div = li.find('div', class_=["style3_subject", "break-all"])
            ret['title'] = div.find('a').text
            result_list.append(ret)
        
        return {"result_list": result_list, "count": len(result_list)}

async def add_comment_kf(id, content):
    data = {
        'message': content,
        'doctype': 1,
        'return_html': 1,
        'quotepid': 0,
    }
    url = f"{URL_HOST['kf']}/post-create-{id}-1.htm"
    async with ClientSessionSingleton().session_kf.post(url, data=data) as response:
        respTest = await response.text()
        # print(respTest, flush=True)
        return 'true'

async def search_zhaoziyuan(keyword, page=1):
    url = f"{URL_HOST['zhaoziyuan']}/so?filename={keyword}&page={page}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")
            try:
                page = soup.body.select_one(".newsList > .page")
                last_page_a = page.select_one("ul a:last-child")
                purl = urlparse(last_page_a["href"])
                totalpage = parse_qs(purl.query).get("page", [None])[0]

                ul = soup.body.select_one(".newsList")
                list_li = ul.select("li")

                result_list = []
                for li in list_li:
                    div = li.select_one(".news_text")
                    if div == None:
                        continue
                    a = li.select_one("a")
                    h3 = li.select_one("h3")
                    p = li.select_one("p")
                    if a == None or h3 == None or p == None or "href" not in a.attrs:
                        continue

                    result_list.append(
                        {
                            "title": h3.text,
                            "href": f'/api/parse_zhaoziyuan_resid?res_id={a["href"]}',
                            "note": p.text,
                        }
                    )

                return {
                    "result_list": result_list,
                    "count": len(result_list),
                    "totalpage": totalpage,
                }

            except Exception as e:
                traceback.print_exc()
                raise Exception("html文档解析失败")


async def parse_zhaoziyuan_resid(res_id):
    url = f"{URL_HOST['zhaoziyuan']}/{res_id}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")
            try:
                aTags = soup.body.select(".news_box > a")
                for a in aTags:
                    if "href" in a.attrs:
                        if (
                            "https://www.alipan.com/" in a["href"]
                            or "https://www.aliyundrive.com/"
                        ):
                            return a["href"]

            except Exception as e:
                traceback.print_exc()
                raise Exception("html文档解析失败")


async def search(session, host, keyword, page):
    # print("search", flush=True)
    if not keyword or keyword == "":
        raise Exception("keyword must be not null")

    url = f"{host}/search?keyword={keyword}&page={page}&_={int(time.time()*1000)}"
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
    }
    async with session.get(url, headers=headers) as resp:
        return await resp.json(content_type=None)


async def search_139(session, keyword, page=1):
    # print("search_139", flush=True)
    respJson = await search(session, URL_HOST["139"], keyword, page)
    if "success" in respJson and respJson["success"] == "true":

        def addHost(item):
            for k in ["topic", "question"]:
                if k in item and item[k] != None:
                    ap = item[k]["avatarPath"]
                    item[k]["avatarPath"] = f'{URL_HOST["139"]}/{ap}'
            return item

        respJson["searchResultPage"]["records"] = list(
            map(addHost, respJson["searchResultPage"]["records"])
        )
    return respJson


async def search_189(session, keyword, page=1):
    # print("search_189", flush=True)
    try:
        await check_should_login()
    except Exception as e:
        print("登录189失败")
    return await search(session, URL_HOST["189"], keyword, page)


async def query_topic_list(session, host, page=1):
    # print("query_topic_list", flush=True)
    url = f"{host}/queryTopicList?page={page}&_={int(time.time()*1000)}"
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
    }
    async with session.get(url, headers=headers) as resp:
        return await resp.json(content_type=None)


async def query_topic_list_139(session, page=1):
    # print("query_topic_list_139", flush=True)
    respJson = await query_topic_list(session, URL_HOST["139"], page)
    if "records" in respJson and isinstance(respJson["records"], list):

        def addHost(item):
            item["avatarPath"] = f'{URL_HOST["139"]}/{item["avatarPath"]}'
            return item

        respJson["records"] = list(map(addHost, respJson["records"]))
    return respJson


async def query_topic_list_189(session, page=1):
    # print("query_topic_list_189", flush=True)
    await check_should_login()
    return await query_topic_list(session, URL_HOST["189"], page)


async def query_topic_content(session, host, topicId):
    # print("query_topic_content", flush=True)
    url = f"{host}/queryTopicContent?topicId={topicId}&_={int(time.time()*1000)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
    }
    async with session.get(url, headers=headers) as resp:
        respJson = await resp.json(content_type=None)
        if respJson and isinstance(respJson, object):
            respJson["originHost"] = host
        return respJson


async def query_topic_content_139(session, topicId):
    print("query_topic_content_139", flush=True)
    respJson = await query_topic_content(session, URL_HOST["139"], topicId)

    if respJson and isinstance(respJson, object):
        if "avatarPath" in respJson and respJson["avatarPath"] != None:
            respJson["avatarPath"] = f'{URL_HOST["139"]}/{respJson["avatarPath"]}'
        if (
            "image" in respJson
            and isinstance(respJson["image"], str)
            and "content" in respJson
            and isinstance(respJson["content"], str)
        ):
            imageJson = json.loads(respJson["image"])
            if isinstance(imageJson, list):
                for image in imageJson:
                    s1 = f"{image['path']}{image['name']}"
                    s2 = f"{URL_HOST['139']}/{image['path']}{image['name']}"
                    respJson["content"] = respJson["content"].replace(s1, s2)
    return respJson


async def query_topic_content_189(session, topicId):
    print("query_topic_content_189", flush=True)
    await check_should_login()
    return await query_topic_content(session, URL_HOST["189"], topicId)


async def login(session, host, user, passwd):
    # print("login", flush=True)
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
    }
    url = f"{host}/login?_={int(time.time()*1000)}"
    async with session.get(url, headers=headers) as resp:
        respJson = await resp.json(content_type=None)
        if respJson["showCaptcha"] == "true":
            imgUrl = "captcha/" + respJson["captchaKey"] + ".jpg"
            raise Exception(f"login fail respJson: {respJson}")

        cookies = session.cookie_jar.filter_cookies(url)
        cms_token = cookies.get("cms_token").value

        data = {
            "type": 10,
            "account": user,
            "password": hashlib.sha256(passwd.encode(encoding="utf-8")).hexdigest(),
            "jumpUrl": "",
            "captchaKey": "",
            "captchaValue": "",
            "rememberMe": "false",
            "token": cms_token,
        }
        async with session.post(url, headers=headers, data=data) as resp:
            respJson = await resp.json(content_type=None)
            if "success" not in respJson or respJson["success"] != "true":
                raise Exception(f"login fail, respJson: {respJson}")
            # cookies = session.cookie_jar.filter_cookies(url)
            # cms_accessToken = cookies.get("cms_accessToken").value
            # cms_refreshToken = cookies.get("cms_refreshToken").value
            # print("cms_accessToken", cms_accessToken)
            # print("cms_refreshToken", cms_refreshToken)
    global G_LAST_LOGIN_TIME_189
    G_LAST_LOGIN_TIME_189 = time.time()


async def login_189(session, user, passwd):
    print("login_189", flush=True)
    return await login(session, URL_HOST["189"], user, passwd)


async def add_comment(session, host, topicId, content):
    # print("add_comment", flush=True)
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
    }

    url = f"{host}/user/control/comment/add?_={int(time.time()*1000)}"

    cookies = session.cookie_jar.filter_cookies(url)
    cms_token = cookies.get("cms_token").value
    data = {
        "topicId": topicId,
        "content": content,
        "captchaKey": "",
        "captchaValue": "",
        "token": cms_token,
    }
    async with session.post(url, headers=headers, data=data) as resp:
        respJson = await resp.json(content_type=None)
        if "success" not in respJson or respJson["success"] != "true":
            raise Exception(f"login fail, respJson: {respJson}")
        return respJson


async def add_comment_189(session, topicId, content):
    print("add_comment_189", flush=True)
    await check_should_login()
    return await add_comment(session, URL_HOST["189"], topicId, content)


async def index(request):
    return web.FileResponse("./static/index.html")


async def api_search_pansearch(request):
    print("api_search_pansearch", flush=True)
    try:
        data = await request.json()
        keyword = data["keyword"]
        limit = data["limit"] if "limit" in data else 10
        offset = data["offset"] if "offset" in data else 0
        pan = data["pan"] if "pan" in data else None
        ret = await search_pansearch(keyword, limit, offset, pan)
        return web.json_response({"status": "success", "result": ret})
    except Exception as e:
        traceback.print_exc()
        return web.json_response({"status": "fail", "msg": traceback.format_exc()})


async def api_search_xiaoya(request):
    print("api_search_xiaoya", flush=True)
    try:
        data = await request.json()
        keyword = data["keyword"]
        type = data["type"] if "type" in data else "all"
        ret = await search_xiaoya(keyword, type)
        return web.json_response({"status": "success", "result": ret})
    except Exception as e:
        traceback.print_exc()
        return web.json_response({"status": "fail", "msg": traceback.format_exc()})

async def api_search_kf(request):
    print("api_search_kf", flush=True)
    try:
        data = await request.json()
        keyword = data["keyword"]
        ret = await search_kf(keyword)
        return web.json_response({"status": "success", "result": ret})
    except Exception as e:
        traceback.print_exc()
        return web.json_response({"status": "fail", "msg": traceback.format_exc()})
    
async def api_add_comment_kf(request):
    print("api_add_comment_kf", flush=True)
    try:
        data = await request.json()
        id = data["id"]
        content = data["content"]
        ret = await add_comment_kf(id, content)
        return web.json_response({"status": "success", "result": ret})
    except Exception as e:
        traceback.print_exc()
        return web.json_response({"status": "fail", "msg": traceback.format_exc()})

async def api_search_zhaoziyuan(request):
    print("api_search_zhaoziyuan", flush=True)
    try:
        data = await request.json()
        keyword = data["keyword"]
        page = data["page"]
        ret = await search_zhaoziyuan(keyword, page)

        return web.json_response({"status": "success", "result": ret})
    except Exception as e:
        traceback.print_exc()
        return web.json_response({"status": "fail", "msg": traceback.format_exc()})


async def api_parse_zhaoziyuan_resid(request):
    print("api_parse_zhaoziyuan_resid", flush=True)
    res_id = request.query.get("res_id")
    aliyundriveUrl = f'{URL_HOST["zhaoziyuan"]}/{res_id}'
    try:
        url = await parse_zhaoziyuan_resid(res_id)
        if url != None:
            aliyundriveUrl = url
    except Exception as e:
        traceback.print_exc()
    return web.HTTPFound(aliyundriveUrl, text=f'<a href="{aliyundriveUrl}">Found</a>')


async def api_search_139(request):
    print("api_search_139", flush=True)
    try:
        data = await request.json()
        keyword = data["keyword"]
        page = data["page"] if "page" in data else 1
        ret = await search_139(ClientSessionSingleton().session_139, keyword, page)
        return web.json_response({"status": "success", "result": ret})
    except Exception as e:
        traceback.print_exc()
        return web.json_response({"status": "fail", "msg": traceback.format_exc()})


async def api_search_189(request):
    print("api_search_189", flush=True)
    try:
        data = await request.json()
        keyword = data["keyword"]
        page = data["page"] if "page" in data else 1
        ret = await search_189(ClientSessionSingleton().session_189, keyword, page)
        return web.json_response({"status": "success", "result": ret})
    except Exception as e:
        traceback.print_exc()
        return web.json_response({"status": "fail", "msg": traceback.format_exc()})


async def api_query_topic_list_139(request):
    print("api_query_topic_list_139", flush=True)
    try:
        data = await request.json()
        page = data["page"] if "page" in data else 1
        ret = await query_topic_list_139(ClientSessionSingleton().session_139, page)
        return web.json_response({"status": "success", "result": ret})
    except Exception as e:
        traceback.print_exc()
        return web.json_response({"status": "fail", "msg": traceback.format_exc()})


async def api_query_topic_list_189(request):
    print("api_query_topic_list_189", flush=True)
    try:
        data = await request.json()
        page = data["page"] if "page" in data else 1
        ret = await query_topic_list_189(ClientSessionSingleton().session_189, page)
        return web.json_response({"status": "success", "result": ret})
    except Exception as e:
        traceback.print_exc()
        return web.json_response({"status": "fail", "msg": traceback.format_exc()})


async def api_query_topic_content_139(request):
    print("api_query_topic_content_139", flush=True)
    try:
        data = await request.json()
        topicId = data["topicId"]
        ret = await query_topic_content_139(
            ClientSessionSingleton().session_139, topicId
        )
        return web.json_response({"status": "success", "result": ret})
    except Exception as e:
        traceback.print_exc()
        return web.json_response({"status": "fail", "msg": traceback.format_exc()})


async def api_query_topic_content_189(request):
    print("api_query_topic_content_189", flush=True)
    try:
        data = await request.json()
        topicId = data["topicId"]
        ret = await query_topic_content_189(
            ClientSessionSingleton().session_189, topicId
        )
        return web.json_response({"status": "success", "result": ret})
    except Exception as e:
        traceback.print_exc()
        return web.json_response({"status": "fail", "msg": traceback.format_exc()})


async def api_add_comment_189(request):
    print("api_add_comment_189", flush=True)
    try:
        data = await request.json()
        topicId = data["topicId"]
        content = data["content"]
        ret = await add_comment_189(
            ClientSessionSingleton().session_189, topicId, content
        )
        return web.json_response({"status": "success", "result": ret})
    except Exception as e:
        traceback.print_exc()
        return web.json_response({"status": "fail", "msg": traceback.format_exc()})


if __name__ == "__main__":
    app = web.Application()
    routes = [
        web.get("/", index),
        web.post("/api/search_pansearch", api_search_pansearch),
        web.post("/api/search_xiaoya", api_search_xiaoya),
        web.post("/api/search_zhaoziyuan", api_search_zhaoziyuan),
        web.get("/api/parse_zhaoziyuan_resid", api_parse_zhaoziyuan_resid),
        web.post("/api/search_139", api_search_139),
        web.post("/api/search_189", api_search_189),
        web.post("/api/search_kf", api_search_kf),
        web.post("/api/addComment_kf", api_add_comment_kf),
        web.post("/api/queryTopicList_139", api_query_topic_list_139),
        web.post("/api/queryTopicList_189", api_query_topic_list_189),
        web.post("/api/queryTopicContent_139", api_query_topic_content_139),
        web.post("/api/queryTopicContent_189", api_query_topic_content_189),
        web.post("/api/addComment_189", api_add_comment_189),
    ]
    routes.append(web.static("/", path="static"))
    app.add_routes(routes)
    loop = asyncio.get_event_loop()

    web.run_app(app, port=PORT_NUMBER, loop=loop)

#!/usr/bin/python3

import traceback
import aiohttp
from aiohttp import web
import asyncio
import time
import hashlib
import json

PORT_NUMBER = 9094

G_LAST_LOGIN_TIME_189 = 0

URL_HOST = {"139": "http://www.91panta.cn", "189": "http://www.leijing.xyz"}


class ClientSessionSingleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.session_139 = aiohttp.ClientSession()
            cls._instance.session_189 = aiohttp.ClientSession()
        return cls._instance


async def check_should_login():
    if time.time() - G_LAST_LOGIN_TIME_189 > 7 * 24 * 60 * 60:
        await login_189(ClientSessionSingleton().session_189, "mugu", "88888888")


async def search_pansearch(keyword, limit=10, offset=0, pan=None):
    url = f"https://www.pansearch.me/api/search?keyword={keyword}&limit={limit}&offset={offset}"
    if pan != None:
        url = f"https://www.pansearch.me/api/search?keyword={keyword}&limit={limit}&offset={offset}&pan={pan}"

    headers = {
        "Host": "www.pansearch.me",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh-Hans;q=0.9",
        "Connection": "keep-alive",
        "Accept-Encoding": "gzip, deflate, br",
        "User-Agent": "PanSearch/2 CFNetwork/1494.0.7 Darwin/23.4.0",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            return await response.json()


async def search(session, host, keyword, page):
    # print("search", flush=True)
    if not keyword or keyword == "":
        raise Exception("keyword must be not null")

    url = f"{host}/search?keyword={keyword}&page={page}&_={int(time.time()*1000)}"
    headers = {
        "X-Requested-With": "XMLHttpRequest",
    }
    async with session.get(url, headers=headers) as resp:
        return await resp.json(content_type=None)


async def search_139(session, keyword, page=1):
    # print("search_139", flush=True)
    respJson = await search(session, URL_HOST["139"], keyword, page)
    if "success" in respJson and respJson["success"] == "true":

        def addHost(item):
            ap = item["topic"]["avatarPath"]
            item["topic"]["avatarPath"] = f'{URL_HOST["139"]}/{ap}'
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
    async with session.get(url) as resp:
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


async def test():
    async with aiohttp.ClientSession() as session:
        if not await login_189(session, "mugu", "88888888"):
            print("login fail")
            return

        ret = await add_comment_189(session, 325, "感谢分享")
        # ret = await queryTopicContent_189(322)
        print(ret)

    # searchRetJson = await search_189("幕府将军")
    # if searchRetJson and searchRetJson["success"]:
    #     searchResultPage = searchRetJson["searchResultPage"]
    #     print(searchResultPage["maxresult"])  # 当前页下的总项数
    #     print(searchResultPage["totalrecord"])  # 总项数
    #     print(searchResultPage["totalpage"])  # 总页数
    #     print(searchResultPage["currentpage"])  # 当前页

    #     for item in searchResultPage["records"]:
    #         topic = item["topic"]
    #         print(topic["id"])
    #         avatarPath = topic["avatarPath"]
    #         avatarName = topic["avatarName"]
    #         print(f"{avatarPath}{avatarName}")
    #         print(topic["nickname"] or topic["account"])
    #         print(topic["lastUpdateTime"] or topic["postTime"])
    #         print(topic["title"])
    #         print(topic["summary"])
    #         print(topic["tagName"])
    #         print(topic["commentTotal"])
    #         print(topic["viewTotal"])


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
        web.post("/api/search_139", api_search_139),
        web.post("/api/search_189", api_search_189),
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

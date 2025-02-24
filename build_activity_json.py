import asyncio
import requests
import json
import os
import datetime


class AuthenticationError(Exception):
    pass

# 飞书多维表格 -> json


APP_TOKEN = os.environ.get("APP_TOKEN", "")
APP_ID = os.environ.get("APP_ID", "")
APP_SECRET = os.environ.get("APP_SECRET", "")


def isMultilineText(arg):
    return isinstance(arg, list)


def isLink(arg):
    return isinstance(arg, dict) and bool(arg["link"])


def convertMultilineTextToString(mlText):
    str = ""
    if mlText:
        for line in mlText:
            if line["type"] == "url":
                str += f'[{line["text"]}]({line["link"]})'
            else:
                str += line["text"]
    return str


def convertMultilineTextToTextArray(mlText):
    arr = []
    if mlText:
        for line in mlText:
            if line["type"] == "url":
                arr.append(f'[{line["text"]}]({line["link"]})')
            else:
                arr.append(line["text"])
    return arr


def extractLinkFromMultilineText(mlText):
    link = ""
    if mlText:
        for line in mlText:
            if line["type"] == "url":
                link = line["link"]
                break
    return link


def endOfTheDay(time):
    # 判断 endTimeStamp 是否为东八区一天的起始时
    if isinstance(time, int) is False:
        return 0
    elif time and time % 28800000 == 0:
        return time + 86400000  # 加上 24 小时的时间戳
    else:
        return time


def requestAccessToken():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    body = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET,
    }
    response = requests.post(url, json=body)
    if response.status_code == 200:
        data = response.json()
        if data["code"] != 0:
            return False
        else:
            globals()["access_token"] = data["tenant_access_token"]
            return True
    else:
        return False


async def requestTableRecords(app_token, table_id, view_id=None, optionalParams=None):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
    access_token = globals().get("access_token")
    # set the header with Authorization access token
    header = {"Authorization": f"Bearer {access_token}"}
    # set the query parameters with view_id if given
    params = {
        "text_field_as_array": True,
    }
    if view_id:
        params["view_id"] = view_id
    if optionalParams:
        params.update(optionalParams)
    # send a get request and return the response
    response = requests.get(url, headers=header, params=params)
    data = response.json()
    if data["code"] != 0:
        return None
    else:
        return data['data']


def parseActivityRecordsToList(records=[]):
    mapping_dict = {"关联键": "key", "备注": "desc", "开始时间": "startTimeStamp",
                    "活动名": "title", "活动链接": "docLink", "类别": "category", "结束时间": "endTimeStamp", "头图": "figure", "附加链接": "addition"}
    list = []

    if records:
        for record in records:
            obj = {mapping_dict[k]: convertMultilineTextToString(
                v) if isMultilineText(v) else v["link"] if (isLink(v) and k != "附加链接") else v for k, v in record["fields"].items()}
            if (obj.get("startTimeStamp") is None or obj.get("endTimeStamp") is None):
                continue
            obj["endTimeStamp"] = endOfTheDay(obj["endTimeStamp"])
            obj["lastModifiedTime"] = record["last_modified_time"]
            list.append(obj)
    return list


def parseActivityRewardToRewardList(records=[], fieldNames={}):
    rules = [{
        "type": "days",
        "rewards": [],
    }, {
        "type": "count",
        "rewards": []
    }]

    customRule = {}

    if records:
        for record in records:
            fields = record["fields"]
            categories = fields.get("指定分类")
            if fields.get("最小天数"):
                rewards = rules[0]["rewards"]
                if isinstance(categories, list):
                    categories.sort()
                    key = "days-"+",".join(categories)
                    if key not in customRule:
                        customRule[key] = {"type": "days",
                                           "rewards": [], "categories": categories}
                    rewards = customRule[key]["rewards"]
                rewards.append({
                    "name": convertMultilineTextToString(fields.get(fieldNames["reward"])),
                    "count": int(fields.get("最小天数")),
                    "recommend_count": int(fields.get("文章被推荐数量") or 0)
                })
            elif fields.get("数量"):
                rewards = rules[1]["rewards"]
                if isinstance(categories, list):
                    categories.sort()
                    key = "count-"+",".join(categories)
                    if key not in customRule:
                        customRule[key] = {"type": "count",
                                           "rewards": [], "categories": categories}
                    rewards = customRule[key]["rewards"]
                rewards.append({
                    "name": convertMultilineTextToString(fields.get(fieldNames["reward"])),
                    "count": int(fields.get("数量")),
                    "recommend_count": int(fields.get("文章被推荐数量") or 0)
                })
    rules.extend(customRule.values())
    for i, item in enumerate(rules):
        item["rewards"] = sorted(item.get("rewards"),
                                 key=lambda reward: reward.get("count"))
    return rules

def parseActivityPointRulesToPointRuleList(records=[]):
    rules = []

    mapping_dict = {
        "合格": "valid",
        "推荐": "recommend",
        "阅读达到指定数量": "view"
    }
    if records:
        for record in records:
            fields = record["fields"]
            rule = {
                "condition": mapping_dict[fields.get("条件")],
                "point": int(fields.get("增加积分")),
            }
            if ("指定数量" in fields):
                rule["amount"] = int(fields.get("指定数量"))

            rules.append(rule)
    return rules

def parseActivityRuleMap(records=[]):
    ruleMap = {
        "categories": [],
        "signSlogan": "",
        "signLink": "",
        "tagNames": [],
        "wordCount": 0,
        "theme": "",
        "recommend": False
    }
    for record in records:
        fields = record["fields"]
        ruleMap["categories"] = fields.get("分类") or []
        ruleMap["tagNames"] = fields.get("标签") or []
        ruleMap["wordCount"] = fields.get("字数") or 0
        ruleMap["theme"] = fields.get("话题") or ""
        ruleMap["signSlogan"] = convertMultilineTextToString(
            fields.get("关键词"))
        ruleMap["signLink"] = extractLinkFromMultilineText(fields.get("关键词"))
        ruleMap["recommend"] = fields.get("要求被官方推荐") or False
    return ruleMap


async def fetchArticleActivitiesAndBuildList():
    today = str(datetime.date.today()-datetime.timedelta(days=7))
    result = await requestTableRecords(APP_TOKEN, "tblM2kMhEmywUdD2", "vewD9xQ8SV", {
        "filter": f'OR(CurrentValue.[结束时间]>=TODATE("{today}"),CurrentValue.[结束时间]="")',
        "sort": '["结束时间 DESC"]',
        "automatic_fields": True
    })
    list = parseActivityRecordsToList(result.get("items"))

    relatedKeys = [item["key"] for item in list]

    activityRewardsTasks = asyncio.gather(*[requestTableRecords(APP_TOKEN, "tblWGtMT5fgnRQ9s", "vewj8t6vAm", {
        "filter": f'CurrentValue.[所属活动]="{key}"',
        "field_names": '["等级名", "最小天数", "数量", "指定分类", "文章被推荐数量"]'
    }) for key in relatedKeys])

    pointActivityRewardsTasks = asyncio.gather(*[requestTableRecords(APP_TOKEN, "tbl00H2pySX4cFaK", "vewj8t6vAm", {
        "filter": f'CurrentValue.[所属活动]="{key}"',
        "field_names": '["增加积分", "条件", "指定数量"]'
    }) for key in relatedKeys]) 

    activityRulesTasks = asyncio.gather(*[requestTableRecords(APP_TOKEN, "tblawuUZtQTY7Tq4", "vewo5RWnaX", {
        "filter": f'CurrentValue.[所属活动]="{key}"',
        "field_names": '["关键词", "分类", "字数", "标签", "话题", "要求被官方推荐"]'
    }) for key in relatedKeys])

    activityRewardsResp = await activityRewardsTasks
    pointActivityRewardsResp = await pointActivityRewardsTasks
    activityRulesResp = await activityRulesTasks
    

    for i, item in enumerate(list):
        if activityRewardsResp[i]:
            rewardList = parseActivityRewardToRewardList(
                activityRewardsResp[i].get("items"), {"reward": "等级名"})
            item["rewards"] = rewardList
        if pointActivityRewardsResp[i]:
            pointRules = parseActivityPointRulesToPointRuleList(
                pointActivityRewardsResp[i].get("items"))
            item["pointRules"] = pointRules
        if activityRulesResp[i] and activityRulesResp[i].get("items"):
            ruleMap = parseActivityRuleMap(activityRulesResp[i].get("items"))
            item.update(ruleMap)

    return list


def parsePinActivityRuleList(records=[]):
    ruleList = []
    for record in records:
        ruleMap = {
            "topic": "",
            "theme": "",
            "jcode": False,
            "keywords": [],
            "subStartTime": 0,
            "subEndTime": 0,
            "subLink": ""
        }
        fields = record["fields"]
        topic = fields.get("话题")
        if (isLink(topic)):
            topic["text"] = topic["text"].strip("#")
        ruleMap["topic"] = topic or None
        ruleMap["theme"] = fields.get("圈子") or []
        ruleMap["jcode"] = fields.get("代码") or False
        ruleMap["keywords"] = convertMultilineTextToTextArray(
            fields.get("内容关键词")) or []
        ruleMap["subStartTime"] = fields.get("子活动起始日期") or 0
        ruleMap["subEndTime"] = endOfTheDay(fields.get("子活动结束日期"))
        ruleMap["subLink"] = extractLinkFromMultilineText(
            fields.get("子活动链接")) or ""
        ruleList.append(ruleMap)
    return ruleList


async def fetchPinActivitiesAndBuildList():
    today = str(datetime.date.today()-datetime.timedelta(days=7))
    result = await requestTableRecords(APP_TOKEN, "tblBJIlND8Yx6eUp", "vewD9xQ8SV", {
        "filter": f'OR(CurrentValue.[结束时间]>=TODATE("{today}"),CurrentValue.[结束时间]="")',
        "sort": '["结束时间 DESC"]',
        "automatic_fields": True
    })
    list = parseActivityRecordsToList(result.get("items"))

    relatedKeys = [item["key"] for item in list]

    activityRewardsTasks = asyncio.gather(*[requestTableRecords(APP_TOKEN, "tbl3heBikj4xtqBG", "vewj8t6vAm", {
        "filter": f'CurrentValue.[所属活动]="{key}"',
        "field_names": '["奖励", "最小天数", "数量"]'
    }) for key in relatedKeys])

    activityRulesTasks = asyncio.gather(*[requestTableRecords(APP_TOKEN, "tblvzVVzHLPaqXS4", "vewo5RWnaX", {
        "filter": f'CurrentValue.[所属活动]="{key}"',
        "field_names": '["话题", "圈子", "代码", "内容关键词", "子活动起始日期", "子活动结束日期", "子活动链接"]'
    }) for key in relatedKeys])

    activityRewardsResp = await activityRewardsTasks
    activityRulesResp = await activityRulesTasks

    for i, item in enumerate(list):
        if activityRewardsResp[i]:
            rewardList = parseActivityRewardToRewardList(
                activityRewardsResp[i].get("items"), {"reward": "奖励"})
            item["rewards"] = rewardList
        if activityRulesResp[i] and activityRulesResp[i].get("items"):
            ruleList = parsePinActivityRuleList(
                activityRulesResp[i].get("items"))
            item["rules"] = ruleList
        item["category"] = "沸点活动"

    return list


async def fetchOtherActivitiesAndBuildList():
    today = str(datetime.date.today())
    result = await requestTableRecords(APP_TOKEN, "tbl5P7tQ0sfJel1B", "vewD9xQ8SV", {
        "filter": f'OR(CurrentValue.[结束时间]>=TODATE("{today}"),CurrentValue.[结束时间]="")',
        "sort": '["结束时间 DESC"]',
        "automatic_fields": True
    })
    list = parseActivityRecordsToList(result.get("items"))
    return list


async def buildActivityJSON():
    aList = await fetchArticleActivitiesAndBuildList()
    list = sorted(
        aList, key=lambda x: x['endTimeStamp'], reverse=True)
    json_object = json.dumps(list, indent=4, ensure_ascii=False)
    with open("activity.json", "w", encoding="utf-8") as outfile:
        outfile.write(json_object)


async def buildPinActivityJSON():
    pList = await fetchPinActivitiesAndBuildList()
    list = sorted(
        pList, key=lambda x: x['endTimeStamp'], reverse=True)
    json_object = json.dumps(list, indent=4, ensure_ascii=False)
    with open("pin_activity.json", "w", encoding="utf-8") as outfile:
        outfile.write(json_object)


async def buildOtherActivityJSON():
    pList = await fetchOtherActivitiesAndBuildList()
    list = sorted(
        pList, key=lambda x: x['endTimeStamp'], reverse=True)
    json_object = json.dumps(list, indent=4, ensure_ascii=False)
    with open("other_activity.json", "w", encoding="utf-8") as outfile:
        outfile.write(json_object)


async def main():
    if (requestAccessToken()):
        await buildActivityJSON()
        await buildPinActivityJSON()
        await buildOtherActivityJSON()
    else:
        raise AuthenticationError("FeiShu request access token")


asyncio.run(main())

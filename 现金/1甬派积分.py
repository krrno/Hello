#cron:10 21 * * *
import os
import math
import time
import requests


# 青龙环境变量名
ENV_NAME = "yp"


def print_banner(total):
    print("｡ﾟﾟ･｡･ﾟﾟ｡")
    print("  ﾟ。  ♡  ｡ﾟ")
    print("    ﾟ･｡･ﾟ")
    print("   (˶ᵔ ᵕ ᵔ˶)")
    print("  /づ    づ")
    print(f"共检测到 {total} 个账号")


def parse_accounts():
    env = os.getenv(ENV_NAME)

    if not env:
        print(f"❌ 未检测到青龙环境变量:{ENV_NAME}")
        print("变量格式:USER_ID#DEVICE_ID#WTOKEN")
        return []

    accounts = []

    for line in env.strip().splitlines():
        line = line.strip()

        if not line:
            continue

        parts = line.split("#")

        if len(parts) < 3:
            print(f"⚠️ 账号格式错误:{line}")
            continue

        user_id = parts[0].strip()
        device_id = parts[1].strip()
        wtoken = parts[2].strip()

        if not user_id or not device_id:
            print(f"⚠️ USER_ID 或 DEVICE_ID 为空:{line}")
            continue

        accounts.append({
            "USER_ID": user_id,
            "DEVICE_ID": device_id,
            "WTOKEN": wtoken
        })

    return accounts


def build_headers(device_id, wtoken):
    return {
        "system": "Android",
        "version": "33",
        "model": "V2148A",
        "appversion": "11.3.2",
        "appbuild": "202505060",
        "deviceid": device_id,
        "wToken": wtoken,
        "Host": "ypapp.cnnb.com.cn"
    }


def get_task_info(user_id, headers):
    url = "https://ypapp.cnnb.com.cn/yongpai-user/api/user/my_level"
    params = {
        "userId": user_id
    }

    res = requests.get(url, headers=headers, params=params, timeout=15)
    return res.json()


def get_news_ids(headers):
    news_ids = []

    def find_news_id(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "newsId" and v:
                    news_ids.append(str(v))
                elif k == "adNewsId" and v:
                    news_ids.append(str(v))
                else:
                    find_news_id(v)

        elif isinstance(obj, list):
            for item in obj:
                find_news_id(item)

    for page in range(1, 6):
        try:
            url = "https://ypapp.cnnb.com.cn/yongpai-news/api/news/list"
            params = {
                "channelId": 0,
                "currentPage": page,
                "timestamp": 0
            }


            res = requests.get(url, headers=headers, params=params, timeout=15)
            data = res.json()

            find_news_id(data)


        except Exception as e:
            print(f"❌ 获取第 {page} 页失败:{e}")
            continue

    return list(dict.fromkeys(news_ids))


def read_news(news_id, user_id, device_id, headers):
    try:
        url = "https://ypapp.cnnb.com.cn/yongpai-news/api/news/detail"
        params = {
            "newsId": news_id,
            "userId": user_id,
            "deviceId": device_id
        }

        res = requests.get(url, headers=headers, params=params, timeout=15)
        data = res.json()

        score = data.get("data", {}).get("score")
        print(f"📖  阅读成功 {score} ✨")
        
        return score

    except Exception as e:
        print("❌ 阅读失败:", e)
        return None


def share_news(news_id, user_id, headers):
    try:
        url = "https://ypapp.cnnb.com.cn/yongpai-ugc/api/forward/news"
        params = {
            "userId": user_id,
            "newsId": news_id,
            "source": 2
        }

        res = requests.get(url, headers=headers, params=params, timeout=15)
        data = res.json()

        print(f"🔗 分享成功 {data['data']} ✨")

        return data.get("data")

    except Exception as e:
        print("❌ 分享失败:", e)
        return None


def like_news(news_id, user_id, device_id, headers):
    try:
        url = "https://ypapp.cnnb.com.cn/yongpai-ugc/api/praise/save_news"
        params = {
            "userId": user_id,
            "newsId": news_id,
            "deviceId": device_id
        }

        res = requests.get(url, headers=headers, params=params, timeout=15)
        data = res.json()

        score = data.get("data", {}).get("score")
        print(f"👍 点赞成功 {score} ✨")

        return score

    except Exception as e:
        print("❌ 点赞失败:", e)
        return None


def run_account(account):
    user_id = account["USER_ID"]
    device_id = account["DEVICE_ID"]
    wtoken = account["WTOKEN"]

    headers = build_headers(device_id, wtoken)

    print("👤 ID: ", user_id)

    funcs = {
        "阅读新闻": lambda news_id: read_news(news_id, user_id, device_id, headers),
        "分享新闻": lambda news_id: share_news(news_id, user_id, headers),
        "点赞": lambda news_id: like_news(news_id, user_id, device_id, headers)
    }

    try:
        task_data = get_task_info(user_id, headers)
    except Exception as e:
        print("❌ 获取任务信息失败:", e)
        return

    if not isinstance(task_data, dict):
        print("❌ 任务信息返回异常")
        return

    if "data" not in task_data or not task_data.get("data"):
        print("❌ 任务信息 data 为空:", task_data)
        return

    user_score_data = task_data.get("data", {})
    today_score = user_score_data.get("accTotalScore", 0)
    current_score = user_score_data.get("score", 0)

    print(f"📊 今日获取:{today_score}")
    print(f"💰 现在积分:{current_score}")

    score_rules = user_score_data.get("scoreRule", [])

    if not score_rules:
        print("⚠️ 未获取到任务规则 scoreRule")
        return

    news_ids = get_news_ids(headers)

    if not news_ids:
        print("⚠️ 没有获取到 newsId")
        return

    print("✅ 获取到文章ID数量:", len(news_ids))

    news_index = 0

    for item in score_rules:
        task_type = item.get("type")

        if task_type not in funcs:
            continue

        dayscore = item.get("dayscore", 0)
        used_score = item.get("usedScore", 0)
        single_score = item.get("score", 0)

        if single_score <= 0:
            print(f"⚠️ {task_type} 单次积分异常")
            continue

        need_score = dayscore - used_score

        if need_score <= 0:
            print(f"✅ {task_type}:已完成")
            continue

        count = math.ceil(need_score / single_score)

        print()
        print(f"📌 {task_type} 还需要执行{count} 次")

        for i in range(count):
            news_id = news_ids[news_index % len(news_ids)]
            news_index += 1

            print(f"➡️ {task_type} 第 {i + 1} 次 文章ID:{news_id}")

            try:
                funcs[task_type](news_id)
            except Exception as e:
                print(f"❌ {task_type} 执行失败:{e}")

            time.sleep(5)
    print()
    print("｡ﾟﾟ･｡･ﾟﾟ｡")
    print("  ﾟ。 收工 ｡ﾟ")
    print("    ﾟ･｡･ﾟ")
    print("   (˶ᵕ︵ᵕ˶)")
    print("  /づ  ☕ づ")

def main():
    accounts = parse_accounts()

    if not accounts:
        return

    print_banner(len(accounts))

    total = len(accounts)

    for index, account in enumerate(accounts, start=1):
        print()
        print(f"========== 账号 {index} / {total} ==========")

        run_account(account)

        if index != total:
            print()
            print("⏳ 等待 5 秒后执行下一个账号...")
            time.sleep(5)

    print()
    print("========== 全部账号执行完成 ==========")


if __name__ == "__main__":
    main()
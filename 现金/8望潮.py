import hashlib
import json
import os
import random
import time
import uuid
from datetime import datetime
from urllib.parse import urlparse

import requests
from gmssl import sm2


# =========================
# 青龙配置
# =========================
# cron: 10 9 * * *
# 环境变量名：wc
# 格式：session_id#account_id#UA
# 多账号换行

ENV_NAME = "wc"
UA1 = "Mozilla/5.0 (Linux; Android 13; V2148A Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/101.0.4951.74 Mobile Safari/537.36;xsb_wangchao;xsb_wangchao;8.0.2;native_app;7.2.0"

HOSTS_FIX = {
    "xmt.taizhou.com.cn": "111.3.157.195",
    "srv-app.taizhou.com.cn": "111.3.157.195",
}


# =========================
# 基础工具
# =========================

def fix_hosts():
    hosts_path = "/etc/hosts"

    try:
        with open(hosts_path, "r") as f:
            content = f.read()

        with open(hosts_path, "a") as f:
            for domain, ip in HOSTS_FIX.items():
                if domain not in content:
                    f.write(f"{ip} {domain}\n")
                    print(f"[hosts修复] {domain} -> {ip}")

    except Exception as e:
        print(f"[hosts修复] 失败: {e}")


def encryptWithSM2(article_id, account_id):
    payload = {
        "timestamp": int(time.time() * 1000),
        "articleId": article_id,
        "accountId": account_id,
    }

    text = json.dumps(payload, separators=(",", ":"))
    crypt_sm2 = sm2.CryptSM2(
        public_key="A50803A27F000D6B310607EBA2A1C899E82872C0B538CA41DB6F0183B4C7E164DAFC6946ABF93C8AF1C0AD96D0E770D29264EF9F907DDBAE97A2A0BB1036D4AC",
        private_key="",
        mode=1
    )

    return crypt_sm2.encrypt(text.encode("utf-8")).hex()


# =========================
# 账号参数
# =========================

def get_accounts():
    env_data = os.getenv(ENV_NAME)

    if not env_data:
        print(f"❌ 未检测到青龙环境变量：{ENV_NAME}")
        print("格式：session_id#account_id#UA")
        raise SystemExit(1)

    accounts = []

    for line_no, line in enumerate(env_data.strip().splitlines(), 1):
        line = line.strip()

        if not line:
            continue

        parts = line.split("#", 2)

        if len(parts) != 3:
            print(f"⚠️ 第 {line_no} 行格式错误，已跳过：{line}")
            continue

        session_id, account_id, UA = [i.strip() for i in parts]

        if not all([account_id, session_id, UA]):
            print(f"⚠️ 第 {line_no} 行存在空字段，已跳过：{line}")
            continue

        accounts.append({
            "account_id": account_id,
            "session_id": session_id,
            "UA": UA,
        })

    if not accounts:
        print("❌ 未读取到有效账号")
        raise SystemExit(1)

    return accounts


# =========================
# 信息读取
# =========================

def make_account_detail_signature(url, session_id):
    request_id = str(uuid.uuid4())
    timestamp = str(int(time.time() * 1000))

    parsed = urlparse(url)
    sign_path = parsed.path
    sign_str = f"{sign_path}&&{session_id}&&{request_id}&&{timestamp}&&FR*r!isE5W&&64"
    signature = hashlib.sha256(sign_str.encode("utf-8")).hexdigest()

    return signature, request_id, timestamp


def build_account_detail_headers(target_url, account_id, session_id, UA):
    signature, request_id, timestamp = make_account_detail_signature(target_url, session_id)

    return {
        "X-SESSION-ID": session_id,
        "X-REQUEST-ID": request_id,
        "X-TIMESTAMP": timestamp,
        "X-SIGNATURE": signature,
        "X-TENANT-ID": "64",
        "User-Agent": UA,
        "X-ACCOUNT-ID": account_id,
        "Host": "vapp.taizhou.com.cn",
    }


def read_account_detail(account_id, session_id, UA):
    url = "https://vapp.taizhou.com.cn/api/user_mumber/account_detail"
    headers = build_account_detail_headers(url, account_id, session_id, UA)

    res = requests.get(url, headers=headers)
    rst = res.json()["data"]["rst"]

    nick_name = rst["nick_name"]
    mobile = rst["mobile"]
    mobile = f"{mobile[:3]}****{mobile[-4:]}"

    print(f"🪪 昵称：{nick_name}")
    print(f"📱 手机号：{mobile}")


# =========================
# 阅读任务
# =========================

def get_read_jsessionid(account_id, session_id, UA):
    url = (
        "https://xmt.taizhou.com.cn/prod-api/user-read/app/login"
        f"?id={account_id}&sessionId={session_id}&deviceId=1"
    )

    headers = {
        "Host": "xmt.taizhou.com.cn",
        "User-Agent": UA1,
        "Referer": "https://xmt.taizhou.com.cn/readingLuck-v5/?gaze_control=01",
    }

    res = requests.get(url, headers=headers)
    return res.cookies.get("JSESSIONID")


def get_article_list(jsessionid, UA):
    date = datetime.now().strftime("%Y%m%d")
    url = f"https://xmt.taizhou.com.cn/prod-api/user-read/list/{date}"

    headers = {
        "User-Agent": UA1,
        "Referer": "https://xmt.taizhou.com.cn/readingLuck-v5/?gaze_control=01",
        "Host": "xmt.taizhou.com.cn",
    }

    cookies = {
        "JSESSIONID": jsessionid,
    }

    res = requests.get(url, headers=headers, cookies=cookies)
    data = res.json()

    return data.get("data", {}).get("articleIsReadList", [])


def show_read_summary(article_list):
    total = len(article_list)
    completed = sum(1 for article in article_list if article.get("isRead") is True)
    unread = sum(1 for article in article_list if article.get("isRead") is False)

    print(f"📊 文章总数: {total}, 已读: {completed}, 未读: {unread}")


def show_read_articles(article_list):
    read_articles = [
        article for article in article_list
        if article.get("isRead") is True
    ]

    for article in read_articles:
        title = article.get("title", "未知标题")
        short_title = title[:15] + "……" if len(title) > 15 else title
        print(f"✅ 已读: {short_title}")


def read_unread_articles(article_list, jsessionid, account_id, UA):
    unread_articles = [
        article for article in article_list
        if article.get("isRead") is False
    ]

    if not unread_articles:
        show_read_articles(article_list)
        return

    print(f"📌 阅读文章还需要执行 {len(unread_articles)} 次")

    read_headers = {
        "Host": "xmt.taizhou.com.cn",
        "Cookie": f"JSESSIONID={jsessionid}",
        "User-Agent": UA,
        "Referer": "https://xmt.taizhou.com.cn/readingLuck-v5/?gaze_control=01",
    }

    for article_index, article in enumerate(unread_articles, 1):
        title = article.get("title", "未知标题")
        short_title = title[:15] + "……" if len(title) > 15 else title

        signature = encryptWithSM2(article["id"], account_id)
        read_url = (
            "https://xmt.taizhou.com.cn/prod-api/already-read/article/new"
            f"?signature={signature}"
        )

        try:
            res = requests.get(read_url, headers=read_headers)
            result = res.json()

            code = result.get("code")
            msg = "阅读成功" if code == 200 else result.get("msg", "阅读失败")

            print(f"📚 {article_index}/{len(unread_articles)} {short_title} -> ✅{msg}")

        except Exception as e:
            print(f"📚 {short_title} -> 请求失败: {e}")

        time.sleep(random.uniform(5, 8))


def run_read_task(account_id, session_id, UA):
    jsessionid = get_read_jsessionid(account_id, session_id, UA)

    if not jsessionid:
        print("❌ 获取阅读 JSESSIONID 失败")
        return

    article_list = get_article_list(jsessionid, UA)

    show_read_summary(article_list)
    read_unread_articles(article_list, jsessionid, account_id, UA)


# =========================
# 抽奖任务
# =========================

def get_luck_cookie(account_id, session_id, UA):
    url = "https://srv-app.taizhou.com.cn/tzrb/user/loginWC"

    headers = {
        "Host": "srv-app.taizhou.com.cn",
        "User-Agent": UA1,
        "Referer": "https://srv-app.taizhou.com.cn/luckdraw-ra-1/",
    }

    params = {
        "accountId": account_id,
        "sessionId": session_id,
    }

    response = requests.get(url, params=params, headers=headers)
    cookies_dict = response.cookies.get_dict()

    if cookies_dict:
        return "; ".join([f"{k}={v}" for k, v in cookies_dict.items()])

    return None


def cj(jsessionid, UA):
    url = "https://srv-app.taizhou.com.cn/tzrb/userAwardRecordUpgrade/saveUpdate"
    payload = "activityId=67&sessionId=undefined&sig=undefined&token=undefined"

    headers = {
        "Host": "srv-app.taizhou.com.cn",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": UA1,
        "Referer": "https://srv-app.taizhou.com.cn/luckdraw-ra-1/",
        "Cookie": jsessionid,
    }

    print("🎰 开始抽奖...")

    response = requests.post(url, data=payload, headers=headers)
    result = response.json()

    if result.get("code") == 200:
        print("✅ 抽奖成功")
        award = query_award_records(jsessionid, UA, show_records=False)

        if award:
            print(f"🎁 获得: {award}")
    else:
        error_msg = result.get("message", "未知错误")
        print(f"❌ 抽奖失败: {error_msg}")


def query_award_records(jsessionid, UA, show_records=True):
    url = (
        "https://srv-app.taizhou.com.cn/tzrb/userAwardRecordUpgrade/pageList"
        "?pageSize=10&pageNum=1&activityId=67"
    )

    headers = {
        "Host": "srv-app.taizhou.com.cn",
        "User-Agent": UA1,
        "Referer": "https://srv-app.taizhou.com.cn/luckdraw-ra-1/",
        "Cookie": jsessionid,
    }

    res = requests.get(url, headers=headers)
    result = res.json()

    records = result.get("data", {}).get("records", [])

    if not records:
        if show_records:
            print("📜 暂无中奖记录")
        return None

    latest_award_name = records[0].get("awardName", "未知奖品")

    if show_records:
        print("📜 最近中奖记录:")

        for record in records[:5]:
            create_time = record.get("createTime", "未知时间")
            award_name = record.get("awardName", "未知奖品")
            print(f"  {create_time} -> {award_name}")

    return latest_award_name


def run_luck_task(account_id, session_id, UA):
    luck_cookie = get_luck_cookie(account_id, session_id, UA)

    if not luck_cookie:
        print("❌ 获取抽奖 Cookie 失败")
        return

    cj(luck_cookie, UA)
    query_award_records(luck_cookie, UA)


# =========================
# 单账号流程
# =========================

def run_account(account, index, total_accounts):
    account_id = account["account_id"]
    session_id = account["session_id"]
    UA = account["UA"]

    print(f"\n========== 账号 {index} / {total_accounts} ==========")

    try:
        read_account_detail(account_id, session_id, UA)
        run_read_task(account_id, session_id, UA)
        run_luck_task(account_id, session_id, UA)

    except Exception as e:
        print(f"❌ 第 {index} 个账号执行异常: {e}")


# =========================
# 主入口
# =========================

def main():
    fix_hosts()

    accounts = get_accounts()

    print(f"✅ 共读取到 {len(accounts)} 个账号")

    for index, account in enumerate(accounts, 1):
        run_account(account, index, len(accounts))

        if index != len(accounts):
            print("⏳ 等待 3 秒后执行下一个账号")
            time.sleep(3)

    print("\n🎉 全部账号执行完成")


if __name__ == "__main__":
    main()

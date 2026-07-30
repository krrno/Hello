#cron:40 9,22 * * *
import os
import requests
import hashlib
import random
import time

BANNER = """｡ﾟﾟ･｡･ﾟﾟ｡
  ﾟ。  ♡  ｡ﾟ
    ﾟ･｡･ﾟ
   (˶ᵔ ᵕ ᵔ˶)
  /づ    づ"""


def ql_notify(title, content):
    try:
        from notify import send
        send(title, content)
    except Exception as e:
        print(f"⚠️ 青龙通知发送失败：{e}")


def get_accounts():
    env = os.getenv("fxsh") or os.getenv("FXSH") or ""
    accounts = []

    for line in env.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "#" not in line:
            print(f"⚠️ 账号配置格式错误，已跳过：{line}")
            continue

        did, token = line.split("#", 1)
        did = did.strip()
        token = token.strip()
        if not did or not token:
            print(f"⚠️ 账号配置不完整，已跳过：{line}")
            continue

        accounts.append((did, token))

    return accounts

def md5(s):
    return hashlib.md5(s.encode()).hexdigest()
def obj_to_query_string(obj):
    return "&".join(
        f"{k}={v}"
        for k, v in sorted(obj.items())
        if v is not None and not isinstance(v, (dict, list))
    )
def build_headers(body):
    timestamp = int(time.time() * 1000)
    params = {
        "traceid": md5(str(timestamp) + str(random.random())),
        "noncestr": str(random.random())[2:10],
        "timestamp": timestamp,
        "platform": "h5",
        "did": DID,
        "version": "1.0.0",
        "token": TOKEN,
    }
    params["sign"] = md5(obj_to_query_string(body) + obj_to_query_string(params) + "粉象好牛逼a8c19d8267527ea4c7d2f011acf7766f")

    return {
        **{k: str(v) for k, v in params.items()},
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; V2148A Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/101.0.4951.74 Mobile Safari/537.36 AgentWeb/5.0.0 UCBrowser/11.6.4.950",
        "Content-Type": "application/json",
    }


def build_njia_headers(body):
    timestamp = int(time.time() * 1000)
    params = {
        "traceid": md5(str(timestamp) + str(random.random())),
        "noncestr": str(random.random())[2:10],
        "timestamp": timestamp,
        "platform": "android",
        "did": DID,
        "version": "6.9.2",
        "token": TOKEN,
    }
    params["sign"] = md5("粉象好牛逼nb3b16f5a02479a0e34df78d14aefe76" + obj_to_query_string(body) + obj_to_query_string(params))

    return {
        **{k: str(v) for k, v in params.items()},
        "User-Agent": "okhttp-okgo/jeasonlzy",
    }


# 查询我的页面信息
def print_my_page_info():
    url = "https://api.fenxianglife.com/njia/users/myPageInfo"
    body = {}

    data = requests.get(url, headers=build_njia_headers(body), timeout=15).json()
    user_data = data.get("data", {})

    nickname = user_data.get("nickname")
    available_amount = user_data.get("availableAmount", 0) / 100

    notify_lines = []
    if nickname:
        line = f"🙋 昵称：{nickname}"
        print(line)
        notify_lines.append(line)
    line = f"🏦 余额：{available_amount:.2f} 元"
    print(line)
    notify_lines.append(line)
    return notify_lines


# 签到
def sign_reward():
    url = "https://fenxiang-lottery-api.fenxianglife.com/fenxiang-lottery/user/sign/reward"
    body = {}

    data = requests.post(url, headers=build_headers(body), json=body, timeout=15).json()
    code = data.get("code")
    message = data.get("message")

    if code == 200 and message == "success":
        print("🗓️ 签到：签到成功")
    elif code == 20002:
        print(f"🗓️ 签到：{message}")
        print("🚀 任务：开始执行")


# 获取任务
def get_task_ids():
    url = "https://fenxiang-lottery-api.fenxianglife.com/fenxiang-lottery/home/data/V2"
    body = {"plateform": "android", "version": "6.9.1"}

    data = requests.post(url, headers=build_headers(body), json=body, timeout=15).json()

    task_result = data.get("data", {}).get("taskModule", {}).get("taskResult", [])

    if isinstance(task_result, dict):
        task_result = [task_result]

    return [item.get("id") for item in task_result if isinstance(item, dict) and item.get("id")]

# 完成任务
def finish_task(task_id):
    url = "https://fenxiang-lottery-api.fenxianglife.com/fenxiang-lottery/lotteryCode/task/finish"
    body = {"taskId": task_id}

    requests.post(url, headers=build_headers(body), json=body, timeout=15)


# 查询中奖码
def print_reward_codes():
    url = "https://fenxiang-lottery-api.fenxianglife.com/fenxiang-lottery/home/data/V2"
    body = {"plateform": "android", "version": "6.9.2"}

    data = requests.post(url, headers=build_headers(body), json=body, timeout=15).json()
    codes = data.get("data", {}).get("openLotteryModule", {}).get("now", {}).get("rewardCodes", [])

    for item in codes:
        code = item.get("code")
        if code:
            print(f"🎫 抽奖码：{code}")


# 查询中奖结果
def print_withdraw_result():
    url = "https://fenxiang-lottery-api.fenxianglife.com/fenxiang-lottery/withdraw/index"
    body = {}

    data = requests.get(url, headers=build_headers(body), timeout=15).json()
    withdraw_data = data.get("data", {})
    date_str = withdraw_data.get("dateStr", "")
    total_reward_amount = withdraw_data.get("totalRewardAmount", 0)
    amount_receive_status = withdraw_data.get("amountReceiveStatus")

    notify_lines = []
    line = f"📆 昨日开奖：{date_str}期"
    print(line)
    notify_lines.append(line)
    if total_reward_amount:
        reward_amount = f"{total_reward_amount / 100:.2f}".rstrip("0").rstrip(".")
        line = f"🏆 昨日中奖：现金 {reward_amount} 元"
        print(line)
        notify_lines.append(line)

        if amount_receive_status == 1:
            print("📥 昨日奖励：未领取")
            receive_url = "https://fenxiang-lottery-api.fenxianglife.com/fenxiang-lottery/periodical/open/result/receiveAll"
            receive_body = {}
            receive_data = requests.post(
                receive_url,
                headers=build_headers(receive_body),
                json=receive_body,
                timeout=15,
            ).json()
            if receive_data.get("message") == "success":
                print("✅ 昨日奖励：领取成功")
        elif amount_receive_status == 2:
            print("📦 昨日奖励：已领取")
    else:
        line = "🏆 昨日中奖：未中奖"
        print(line)
        notify_lines.append(line)
    return notify_lines


# 查询账户明细
def print_account_detail():
    url = "https://api.fenxianglife.com/njia/account/detail/v2"
    body = {
        "lastTime": "0",
        "size": "20",
        "lastId": "0",
        "page": "0",
    }

    headers = {
        **build_njia_headers(body),
        "Content-Type": "application/json;charset=utf-8",
    }

    data = requests.post(url, headers=headers, json=body, timeout=15).json()
    month_list = data.get("data", {}).get("list", [])

    for month_item in month_list:
        month_time = month_item.get("time", "")
        income = month_item.get("income", 0) / 100

        if "年" in month_time and "月" in month_time:
            month_time = month_time.split("年", 1)[1].replace("月", "")
            month_time = f"{int(month_time)}月"

        print(f"📈 月度收益：{month_time}收入 {income:.2f} 元")

        detail_list = month_item.get("list", [])
        if detail_list:
            print("📋 领取记录：")

        for item in detail_list[:5]:
            item_time = item.get("time", 0)
            amount = item.get("amount", 0) / 100
            amount_str = f"{amount:.2f}".rstrip("0").rstrip(".")

            time_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(item_time))
            print(f"⏰ {time_str}  |  💸 入账 {amount_str} 元")


def run_account(index, total, did, token):
    global DID, TOKEN
    DID = did
    TOKEN = token

    print(f"\n========== 账号 {index} / {total} ==========")
    notify_lines = []
    notify_lines.extend(print_my_page_info())
    sign_reward()

    for task_id in get_task_ids():
        finish_task(task_id)

    print_reward_codes()
    notify_lines.extend(print_withdraw_result())

    print_account_detail()
    return notify_lines


def main():
    accounts = get_accounts()

    if not accounts:
        print("❌ 未读取到青龙环境变量 fxsh")
        print("变量格式：did#token")
        return

    total = len(accounts)
    print(BANNER)
    print(f"共检测到 {total} 个账号")

    all_notify_lines = []
    for index, (did, token) in enumerate(accounts, start=1):
        try:
            account_notify_lines = run_account(index, total, did, token)
            if account_notify_lines:
                if all_notify_lines:
                    all_notify_lines.append("")
                all_notify_lines.extend(account_notify_lines)
        except Exception as e:
            print(f"❌ 账号 {index}/{total} 执行异常：{e}")

        if index != total:
            time.sleep(2)

    if all_notify_lines:
        ql_notify("粉象生活", "\n".join(all_notify_lines))


if __name__ == "__main__":
    main()
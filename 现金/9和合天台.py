import os
import time
import uuid
import hashlib
import secrets
import requests
from decimal import Decimal
from urllib.parse import urlparse, parse_qs

try:
    from notify import send
except Exception:
    send = None

# 青龙环境变量名：hhtt
#cron:20 12 * * *
# 多账号换行，格式：
# session#account#client#名字#帐号
# session#account#client

ENV_NAME = "hhtt"


def send_total_notice(content):
    if send:
        try:
            send("和合天台抽奖", content)
        except Exception as e:
            print(f"⚠️ 发送通知失败：{e}")
    else:
        print("⚠️ 未找到 notify.py，跳过通知")


def format_money(amount):
    amount = Decimal(str(amount))
    return str(amount.quantize(Decimal("0.01")).normalize())

# 支付宝绑定 + 提现总开关  1：执行查询/绑定支付宝，并在有余额时提现  0：跳过绑定和提现
BindAlipay = 1
# 解绑支付宝   1：解绑  0：不解绑
Unbind = 0


def parse_account_line(line, line_no=1):
    parts = [i.strip() for i in line.strip().split("#")]

    if len(parts) not in (3, 5):
        print(f"⚠️ 第 {line_no} 行格式错误，已跳过：{line}")
        print("正确格式：session#account#clientId#名字#帐号")
        return None

    if len(parts) == 3:
        session_id, account_id, client_id = parts
        userName, account = "", ""
    else:
        session_id, account_id, client_id, userName, account = parts

    if not all([session_id, account_id, client_id]):
        print(f"⚠️ 第 {line_no} 行必填字段存在空值，已跳过：{line}")
        print("必填字段：session#account#clientId")
        return None

    return {
        "session_id": session_id,
        "account_id": account_id,
        "client_id": client_id,
        "userName": userName,
        "account": account,
    }


def get_env_accounts():
    env = os.getenv(ENV_NAME, "").strip()
    if not env:
        print(f"❌ 未检测到青龙环境变量：{ENV_NAME}")
        print("变量格式：session#account#clientId#名字#帐号")
        return []

    accounts = []
    for line_no, line in enumerate(env.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue

        conf = parse_account_line(line, line_no)
        if conf:
            accounts.append(conf)

    return accounts

UA = "Mozilla/5.0 (Linux; Android 13; V2148A Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/101.0.4951.74 Mobile Safari/537.36;xsb_tiantai;xsb_tiantai;4.5.9;native_app;7.10.1"

def run_account(index, total, conf):
    session_id = conf["session_id"]
    account_id = conf["account_id"]
    client_id = conf["client_id"]
    userName = conf["userName"]
    account = conf["account"]

    print(f"\n========== 账号 {index} / {total} ==========")

    url = "https://act.tmlyun.com/activity-api/task/h5/auth/userLogin"

    headers = {
        "User-Agent": UA,
        "Content-Type": "application/json",
        "Host": "act.tmlyun.com"
    }

    buoy_url = "https://vapp.tmuyun.com/api/buoy/list"
    request_id = str(uuid.uuid4())
    timestamp = str(int(time.time() * 1000))
    sign_str = f"/api/buoy/list&&{session_id}&&{request_id}&&{timestamp}&&FR*r!isE5W&&5"
    signature = hashlib.sha256(sign_str.encode("utf-8")).hexdigest()

    buoy_headers = {
        "X-SESSION-ID": session_id,
        "X-REQUEST-ID": request_id,
        "X-TIMESTAMP": timestamp,
        "X-SIGNATURE": signature,
        "X-TENANT-ID": "5",
        "User-Agent": f"4.5.9;{client_id};Vivo V2148A;Android;13;Release;7.10.1",
        "X-ACCOUNT-ID": account_id,
        "Host": "vapp.tmuyun.com",
    }

    buoy_res = requests.get(buoy_url, headers=buoy_headers)
    buoy_result = buoy_res.json()
    entry_link = buoy_result["data"]["new_up"]["icon_list"][0]["turn_to"]["entryLink"]
    task_q = parse_qs(urlparse(entry_link).query)["q"][0]

    payload = {
        "q": task_q,
        "accountId": account_id,
        "sessionId": session_id,
        "tenantCode": "xsb_tiantai"
    }

    res = requests.post(url, headers=headers, json=payload)

    result = res.json()

    data = result["data"]

    nick_name = data["nickName"]
    token = data["token"]
    phone = str(data["phone"])

    print(f"🪪 昵称：{nick_name}")
    print(f"📱 手机号：{phone[:3]}****{phone[-4:]}")

    task_url = "https://act.tmlyun.com/activity-api/task/h5/activity/getHomeUserLevelTaskList"
    task_headers = {
        "Authorization": token,
        "User-Agent": UA,
        "Host": "act.tmlyun.com"
    }

    task_res = requests.get(task_url, headers=task_headers)
    task_result = task_res.json()

    task_level_id = task_result["data"][0]["taskLevelId"]

    level_task_user_url = (
        "https://act.tmlyun.com/activity-api/task/h5/activity/getLevelTaskUserList"
        f"?levelTaskId={task_level_id}"
    )

    level_task_user_headers = {
        "Authorization": token,
        "User-Agent": UA,
        "Host": "act.tmlyun.com"
    }

    level_task_user_res = requests.get(level_task_user_url, headers=level_task_user_headers)
    level_task_user_result = level_task_user_res.json()
    level_task_user_data = level_task_user_result["data"]

    # ===================== 阅读前检查 =====================
    read_activity_check_url = (
        "https://act.tmlyun.com/activity-api/task/h5/activity/activityCheck"
        f"?yToken=WYSWxVQNbRZFYxRBBEaH7bhwjnfiU%2FjG&sessionId={session_id}&deviceId={client_id}"
    )
    read_activity_check_headers = {
        "Authorization": token,
        "User-Agent": UA,
        "Host": "act.tmlyun.com"
    }
    read_activity_check_res = requests.get(read_activity_check_url, headers=read_activity_check_headers)


    # ===================== 阅读功能 =====================
    def make_read_signature(url):
        request_id = str(uuid.uuid4())
        timestamp = str(int(time.time() * 1000))

        parsed = urlparse(url)
        sign_path = parsed.path

        sign_str = f"{sign_path}&&{session_id}&&{request_id}&&{timestamp}&&FR*r!isE5W&&5"

        signature = hashlib.sha256(sign_str.encode("utf-8")).hexdigest()
        return signature, request_id, timestamp, sign_str


    def build_read_headers(target_url):
        signature, request_id, timestamp, sign_str = make_read_signature(target_url)

        return {
            "X-SESSION-ID": session_id,
            "X-REQUEST-ID": request_id,
            "X-TIMESTAMP": timestamp,
            "X-SIGNATURE": signature,
            "X-TENANT-ID": "5",
            "User-Agent": f"4.5.9;{client_id};Vivo V2148A;Android;13;Release;7.10.1",
            "X-ACCOUNT-ID": account_id,
            "Host": "vapp.tmuyun.com",
        }

    def extract_article_ids(items):
       
        article_ids = []

        for item in items:
            doc_type = item.get("doc_type")

            if str(doc_type) == "2":
                article_id = item.get("id")
                if article_id:
                    article_ids.append(article_id)

            children = item.get("column_news_list") or []
            if children:
                article_ids.extend(extract_article_ids(children))

        return article_ids


    def run_read(need_count, start_index=0):

        url = "https://vapp.tmuyun.com/api/article/channel_list?channel_id=5bee89f21b011b0880b6e49e&isDiFangHao=false&isSheQuHao=false&is_new=true&list_count=0&size=150"
        res = requests.get(url, headers=build_read_headers(url))
        data = res.json()

        article_list = data.get("data", {}).get("article_list", [])

        article_ids = extract_article_ids(article_list)

        start = max(start_index, 0)
        run_ids = article_ids[start:start + need_count]


        for index, article_id in enumerate(run_ids, start=start_index):
            print(f"📚 阅读文章｜文章ID：{article_id}")

            detail_url = f"https://vapp.tmuyun.com/api/article/detail/v2?id={article_id}"
            detail_res = requests.get(detail_url, headers=build_read_headers(detail_url))

            detail_data = detail_res.json()
            message = detail_data.get("message", "")

            if message == "success":
                print("🌟 阅读成功")

            time.sleep(0.5)




    # ===================== 点赞前检查 =====================
    zan_activity_check_url = (
        "https://act.tmlyun.com/activity-api/task/h5/activity/activityCheck"
        f"?yToken=r9oHnllUhmRFYlBVRRfSuPwgnyiI8omJ&sessionId={session_id}&deviceId={client_id}"
    )
    zan_activity_check_headers = {
        "Authorization": token,
        "User-Agent": UA,
        "Host": "act.tmlyun.com"
    }
    zan_activity_check_res = requests.get(zan_activity_check_url, headers=zan_activity_check_headers)
  

    # ===================== 点赞功能 =====================
    def make_zan_signature(sign_path):
        request_id = str(uuid.uuid4())
        timestamp = str(int(time.time() * 1000))

        sign_str = f"{sign_path}&&{session_id}&&{request_id}&&{timestamp}&&FR*r!isE5W&&30"

        signature = hashlib.sha256(sign_str.encode("utf-8")).hexdigest()
        return signature, request_id, timestamp, sign_str


    def make_zan_headers(sign_path):
        signature, request_id, timestamp, sign_str = make_zan_signature(sign_path)

        return {
            "X-SIGNATURE": signature,
            "X-FORUM-TENANT-ID": "30",
            "User-Agent": UA,
            "X-ACCOUNT-ID": account_id,
            "X-TIMESTAMP": timestamp,
            "X-SESSION-ID": session_id,
            "X-REQUEST-ID": request_id,
            "Host": "app.tmuyun.com",
        }


    def get_post_list():
        headers = make_zan_headers("/api/post/list")
        res = requests.get("https://app.tmuyun.com/api/bbs/api/post/list?categoryId=0", headers=headers)
        res.raise_for_status()
        return res.json()


    def zan_post(post_id, status):
        headers = make_zan_headers("/api/post/h5/zan")
        url = f"https://app.tmuyun.com/api/bbs/api/post/h5/zan?id={post_id}&status={status}"

        res = requests.get(url, headers=headers)
        result = res.json()

        if result.get("success") is True:
            if status == 1:
                print("💗 点赞成功")
            else:
                print("🍃 取消点赞")


    def run_zan(need_count, start_index=1, used_post_ids=None):
        if used_post_ids is None:
            used_post_ids = set()

        data = get_post_list()
        records = data.get("data", {}).get("records", [])

        unzan_ids = []

        for item in records:
            if item.get("isZan") == 0:
                post_id = item.get("id")
                if post_id not in used_post_ids:
                    unzan_ids.append(post_id)

        run_ids = unzan_ids[:need_count]


        for index, post_id in enumerate(run_ids, start=start_index):
            print(f"🫶 点赞任务｜帖子ID：{post_id}")

            used_post_ids.add(post_id)

            zan_post(post_id, 1)
            time.sleep(0.5)
            zan_post(post_id, 0)

            time.sleep(0.5)

        return len(run_ids)



    def refresh_level_task_user_data():
        level_task_user_res = requests.get(level_task_user_url, headers=level_task_user_headers)
        level_task_user_result = level_task_user_res.json()
        return level_task_user_result["data"]


    def get_need_count(task):
        task_name = task["name"]
        status = task.get("taskUserStatusBO") or {}

        total = status.get("total", 0)
        complete_num = status.get("completeNum", 0)
        need_count = max(total - complete_num, 0)

        if need_count <= 0:
            print(f"🎉 {task_name}：已完成")
        else:
            print(f"📌 {task_name} 还需要执行 {need_count} 次")

        return need_count


    def get_task_need_count(task_list_name, task_name):
        level_task_user_data = refresh_level_task_user_data()

        for task in level_task_user_data.get(task_list_name, []):
            if task.get("name") == task_name:
                return get_need_count(task)

        return 0


    read_run_index = 0

    while True:
        need_count = get_task_need_count("appBaseList", "阅读文章")
        if need_count <= 0:
            break

        read_run_index += 1
        run_read(1, read_run_index)


    zan_run_index = 0
    used_zan_post_ids = set()

    while True:
        need_count = get_task_need_count("xsqBaseList", "点赞帖子")
        if need_count <= 0:
            break

        zan_run_index += 1
        run_count = run_zan(1, zan_run_index, used_zan_post_ids)
        if run_count <= 0:
            break


    # ===================== 抽奖 token =====================
    lottery_login_url = "https://act.tmlyun.com/activity-api/lottery/api/auth/userLogin"

    lottery_headers = {
        "User-Agent": UA,
        "Content-Type": "application/json",
        "Host": "act.tmlyun.com"
    }

    activity_info_url = "https://act.tmlyun.com/activity-api/task/h5/activity/getActivityInfo"

    activity_info_headers = {
        "Authorization": token,
        "Host": "act.tmlyun.com"
    }

    activity_info_res = requests.get(activity_info_url, headers=activity_info_headers)
    activity_info_result = activity_info_res.json()
    lottery_button_url = activity_info_result["data"]["activityStyle"]["lotteryButtonUrl"]
    lottery_q = parse_qs(urlparse(lottery_button_url).query)["q"][0]

    lottery_payload = {
        "q": lottery_q,
        "accountId": account_id,
        "sessionId": session_id,
        "tenantCode": "xsb_tiantai"
    }

    lottery_res = requests.post(lottery_login_url, headers=lottery_headers, json=lottery_payload)
    lottery_result = lottery_res.json()
    lottery_data = lottery_result["data"]
    lottery_token = lottery_data["token"]
    third_id = lottery_data["thirdId"]  

    # ===================== 查询抽奖次数 =====================
    lottery_num_url = f"https://act.tmlyun.com/activity-api/lottery/h5/activity/lottery/frontPageNum?activityId={third_id}"

    lottery_num_headers = {
        "Authorization": lottery_token,
        "User-Agent": UA,
        "Host": "act.tmlyun.com"
    }

    lottery_num_res = requests.get(lottery_num_url, headers=lottery_num_headers)
    lottery_num_result = lottery_num_res.json()

    remain_prize_num = lottery_num_result["data"]["remainPrizeNum"]
    print(f"🎫 可抽奖次数：{remain_prize_num}")


    # ===================== 执行抽奖 =====================
    if remain_prize_num > 0:
        lottery_draw_url = "https://act.tmlyun.com/activity-api/lottery/h5/activity/lottery/userActivityLottery"

        lottery_draw_headers = {
            "Authorization": lottery_token,
            "User-Agent": UA,
            "Content-Type": "application/json",
            "Host": "act.tmlyun.com"
        }

        lottery_draw_payload = {
            "activityId": third_id,
            "clientId": client_id,
            "prizeVersion": 0
        }

        for index in range(1, remain_prize_num + 1):
            print(f"🌀 开始第 {index} 次抽奖")

            lottery_draw_res = requests.post(
                lottery_draw_url,
                headers=lottery_draw_headers,
                json=lottery_draw_payload
            )

            lottery_draw_result = lottery_draw_res.json()

            if str(lottery_draw_result.get("message", "")).startswith("用户信息未填写"):
                print("⚠️ 用户信息未填写 结束")
                return
            if lottery_draw_result.get("success") is True and lottery_draw_result.get("data"):
                lottery_data = lottery_draw_result["data"]
                prize_name = lottery_data.get("prizeName")

                if lottery_data.get("isPrize") == 0:
                    print("🏅 抽奖成功：谢谢参与")
                elif prize_name:
                    print(f"🏅 抽奖结果：现金{prize_name}")
                else:
                    print(f"🏅 抽奖成功：{lottery_data}")


    # ===================== 获取钱包 U =====================
    wallet_u_url = "https://act.tmlyun.com/activity-api/lottery/h5/activity/lottery/accountPrizeRecord/jumpEquityWallet"

    wallet_u_headers = {
        "Authorization": lottery_token,
        "User-Agent": UA,
        "Host": "act.tmlyun.com"
    }

    wallet_u_res = requests.get(wallet_u_url, headers=wallet_u_headers)
    wallet_u_result = wallet_u_res.json()
    wallet_u_url_data = wallet_u_result["data"]
    wallet_u = parse_qs(urlparse(wallet_u_url_data).query)["u"][0]

    # ===================== 获取钱包 token =====================
    wallet_login_url = "https://my.tmlyun.com/equity-api/user/auth/userLogin"

    wallet_headers = {
        "User-Agent": UA,
        "Content-Type": "application/json",
        "Host": "my.tmlyun.com"
    }

    wallet_payload = {
        "u": wallet_u,
        "accountId": account_id,
        "sessionId": session_id
    }

    wallet_res = requests.post(wallet_login_url, headers=wallet_headers, json=wallet_payload)
    wallet_result = wallet_res.json()
    wallet_data = wallet_result["data"]
    wallet_token = wallet_data["token"]

    # ===================== 查询钱包总金额 =====================
    wallet_info_url = f"https://my.tmlyun.com/equity-api/redBag/getWalletInfo?device={client_id}"

    wallet_info_headers = {
        "Authorization": wallet_token,
        "User-Agent": UA,
        "Host": "my.tmlyun.com"
    }

    wallet_info_res = requests.get(wallet_info_url, headers=wallet_info_headers)
    wallet_info_result = wallet_info_res.json()
    wallet_info_data = wallet_info_result["data"][0]

    total_price = wallet_info_data["totalPrice"]
    total_trans_price = wallet_info_data["totalTransPrice"]
    ali_pay_total_price = wallet_info_data["aliPayTotalPrice"]

    print(f"💎 累计现金：{total_price}")
    print(f"🏦 累计提现：{total_trans_price}")
    print(f"🪙 当前余额：{ali_pay_total_price}")

    # ===================== 解绑支付宝 =====================
    if Unbind == 1:
        unbind_alipay_url = "https://my.tmlyun.com/equity-api/redBag/unBindAliPayAccount"
        unbind_alipay_headers = {
            "Authorization": wallet_token,
            "User-Agent": UA,
            "Host": "my.tmlyun.com"
        }

        unbind_alipay_res = requests.get(unbind_alipay_url, headers=unbind_alipay_headers)
        unbind_alipay_result = unbind_alipay_res.json()

        unbind_alipay_message = unbind_alipay_result.get("message")

        if unbind_alipay_message == "success":
            print("⛓️‍💥 支付宝解绑成功")
        else:
            print(f"⛓️‍💥 {unbind_alipay_message}")

    # ===================== 查询支付宝 / 绑定支付宝 + 提现 =====================
    alipay_detail_url = "https://my.tmlyun.com/equity-api/redBag/getFundsDetail?fundsChannelType=0"

    alipay_detail_headers = {
        "Authorization": wallet_token,
        "User-Agent": UA,
        "Host": "my.tmlyun.com"
    }

    alipay_detail_res = requests.get(alipay_detail_url, headers=alipay_detail_headers)
    alipay_detail_result = alipay_detail_res.json()
    alipay_detail_data = alipay_detail_result["data"]

    real_name = alipay_detail_data["realName"]
    alipay_account = alipay_detail_data["account"]
    aliPayBound = False

    if real_name and alipay_account:
        aliPayBound = True
        print(f"🔒 已绑定支付宝：{real_name} / {alipay_account}")
    else:
        print("🔑 未绑定支付宝")
        if not userName or not account:
            print("⏭️ 未配置支付宝信息")

        if BindAlipay == 1:
            if userName and account:
                bind_alipay_url = f"https://my.tmlyun.com/equity-api/redBag/saveAliPayAccount?userName={userName}&account={account}"

                bind_alipay_headers = {
                    "Authorization": wallet_token,
                    "User-Agent": UA,
                    "Host": "my.tmlyun.com"
                }

                bind_alipay_res = requests.get(bind_alipay_url, headers=bind_alipay_headers)
                bind_alipay_result = bind_alipay_res.json()

                if bind_alipay_result["message"] == "success":
                    aliPayBound = True
                    print(f"🪄 绑定成功：{userName} / {account}")

    # ===================== 审核记录 =====================
    pending_audit_list = []

    if BindAlipay == 1:
        audit_record_url = "https://my.tmlyun.com/equity-api/redBag/pageWalletDetail?current=1&pageSize=20&fundsChannelType=0"

        audit_record_headers = {
            "Authorization": wallet_token,
            "User-Agent": UA,
            "Host": "my.tmlyun.com"
        }

        audit_record_res = requests.get(audit_record_url, headers=audit_record_headers)
        audit_record_result = audit_record_res.json()
        audit_record_list = audit_record_result.get("data", [])

        pending_audit_list = [
            item for item in audit_record_list
            if item.get("status") == "待审核"
        ]

        if pending_audit_list:
            for item in pending_audit_list:
                print(f"⏳ 待审核提现：{item.get('price')}元｜{item.get('createdAt')}")

    # ===================== 提现 =====================
    if BindAlipay != 1:
        print("🛑 已关闭绑定提现")
    elif aliPayBound and not pending_audit_list:
        if ali_pay_total_price > 0:
            withdraw_url = f"https://my.tmlyun.com/equity-api/redBag/createTrans?price={ali_pay_total_price}&fundsChannelType=0&yToken={session_id}&deviceId={client_id}"

            withdraw_headers = {
                "Authorization": wallet_token,
                "User-Agent": UA,
                "Host": "my.tmlyun.com"
            }

            withdraw_res = requests.get(withdraw_url, headers=withdraw_headers)
            withdraw_result = withdraw_res.json()
            withdraw_message = withdraw_result["message"]

            if withdraw_message == "success":
                print("🌈 提现成功")

    # ===================== 查询中奖记录 =====================
    prize_record_url = f"https://act.tmlyun.com/activity-api/lottery/h5/activity/lottery/accountPrizeRecord/userPrizeRecord?activityId={third_id}"

    prize_record_headers = {
        "Authorization": lottery_token,
        "User-Agent": UA,
        "Host": "act.tmlyun.com"
    }

    prize_record_res = requests.get(prize_record_url, headers=prize_record_headers)
    prize_record_result = prize_record_res.json()
    prize_record_list = prize_record_result["data"]["activityAccountPrizeVoList"]

    print("📜 中奖记录")
    total_prize_money = Decimal("0")
    today_prize_money = Decimal("0")
    month_name = ""
    today = time.strftime("%Y-%m-%d")

    for prize_record in prize_record_list:
        prize_name_full = prize_record["prizeName"]

        if ":" in prize_name_full:
            prize_title, prize_money = prize_name_full.split(":", 1)

            if not month_name:
                month_name = prize_title.replace("阅读红包", "").strip()

            try:
                money = Decimal(str(prize_money).replace("元", "").strip())
                total_prize_money += money

                create_time = str(prize_record.get("createTime", ""))
                if create_time.startswith(today):
                    today_prize_money += money
            except Exception:
                pass

    for prize_record in prize_record_list[:5]:
        prize_name = prize_record["prizeName"].split(":")[-1]
        create_time = prize_record["createTime"]
        redeem_end_time_string = prize_record["redeemEndTimeString"]
        redeem_end_date = redeem_end_time_string.split(" ")[0]

        print(f"🕰️ {create_time}｜现金{prize_name}元｜{redeem_end_date} 过期")

    if month_name:
        print(f"📊 {month_name}中奖金额：{format_money(total_prize_money)}元")
    else:
        print(f"📊 中奖金额：{format_money(total_prize_money)}元")
    return today_prize_money



if __name__ == "__main__":
    accounts = get_env_accounts()
    if not accounts:
        raise SystemExit

    total = len(accounts)
    print(f"共检测到 {total} 个账号")

    today_total_prize_money = Decimal("0")

    for i, conf in enumerate(accounts, start=1):
        try:
            account_today_money = run_account(i, total, conf) or Decimal("0")
            today_total_prize_money += account_today_money
        except Exception as e:
            print(f"❌ 账号 {i} 执行异常：{e}")

    today = time.strftime("%Y-%m-%d")
    notify_content = f"{today}\n今日中奖总额：{format_money(today_total_prize_money)}元"
    print(f"\n📮 和合天台抽奖\n{notify_content}")
    send_total_notice(notify_content)
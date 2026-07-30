#cron:20 12 * * *
import os
import json
import re
import time
import requests
from datetime import datetime
from decimal import Decimal

try:
    from notify import send
except Exception:
    send = None

# 青龙环境变量名：yongpai
# 多账号换行，格式：
# accountId#sessionId#deviceid#userName#account
ENV_NAME = "yongpai"

# 开关变量
farmSwitch = 1      # 1=执行农场，0=跳过农场
lotterySwitch = 1   # 1=执行兑换抽奖，0=跳过兑换抽奖
unbindAliPay = 0    # 1=前解绑支付宝，0=不前解绑支付宝
bindAliPay = 1      # 1=绑定支付宝，0=不绑定支付宝
txbindAliPay = 1     #  1=提现， 0=不提醒
hunbindAliPay = 0   # 1=后解绑支付宝，0=不后解绑支付宝

UA = "Mozilla/5.0 (Linux; Android 13; V2148A Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/101.0.4951.74 Mobile Safari/537.36 agentweb/4.0.2 UCBrowser/11.6.4.950 yongpai"

farm_headers = {
    "User-Agent": UA,
}


def loads_json(res):
    return json.loads(res.content.decode("utf-8-sig"))

#延迟
def delay_run():
    time.sleep(0.5)


def post_form(url, data, headers=None):
    delay_run()
    files = {k: (None, str(v)) for k, v in data.items()}
    res = requests.post(url, headers=headers, files=files, timeout=20)
    return loads_json(res)


def request_json(method, url, **kwargs):
    delay_run()
    kwargs.setdefault("timeout", 20)
    try:
        return requests.request(method, url, **kwargs).json()
    except Exception as e:
        return {"_error": str(e)}


def send_total_notice(content):
    if send:
        try:
            send("甬派抽奖", content)
        except Exception as e:
            print(f"⚠️ 发送通知失败：{e}")
    else:
        print("⚠️ 未找到 notify.py，跳过通知")


prize_record_text = ""


def format_money(value):
    return format(value.normalize(), "f")


def calc_today_prize_total(prize_record_text):
    today = datetime.now().strftime("%Y-%m-%d")
    total_amount = Decimal("0")

    for line in prize_record_text.splitlines():
        if today in line:
            match = re.search(r"现金\s*([0-9]+(?:\.[0-9]+)?)\s*元", line)
            if match:
                total_amount += Decimal(match.group(1))

    return format_money(total_amount)


def get_env_accounts():
    env = os.getenv(ENV_NAME, "").strip()
    if not env:
        print(f"❌ 未检测到青龙环境变量：{ENV_NAME}")
        print("变量格式：accountId#deviceid#sessionId#userName#account")
        return []

    accounts = []
    for line_no, line in enumerate(env.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue

        parts = [i.strip() for i in line.split("#")]
        if len(parts) not in (3, 5):
            print(f"⚠️ 第 {line_no} 行格式错误，已跳过：{line}")
            print("正确格式：accountId#deviceid#sessionId[#userName#account]")
            continue

        if len(parts) == 3:
            accountId, deviceid, sessionId = parts
            userName, account = "", ""
        else:
            accountId, deviceid, sessionId, userName, account = parts

        if not all([accountId, deviceid, sessionId]):
            print(f"⚠️ 第 {line_no} 行必填字段存在空值，已跳过：{line}")
            print("必填字段：accountId#deviceid#sessionId")
            continue

        accounts.append({
            "accountId": accountId,
            "sessionId": sessionId,
            "deviceid": deviceid,
            "userName": userName,
            "account": account,
        })

    return accounts


def run_account(index, total, conf):
    accountId = conf["accountId"]
    sessionId = conf["sessionId"]
    deviceid = conf["deviceid"]
    userName = conf["userName"]
    account = conf["account"]

    print(f"\n========== 账号 {index} / {total} ==========")

    # 登录
    login_result = request_json(
        "POST",
        "https://act.tmlyun.com/activity-api/lottery/api/auth/userLogin",
        headers={
            "User-Agent": UA,
            "X-TOKEN": "",
            "X-REQUEST-ID": "",
            "Host": "act.tmlyun.com"
        },
        json={
            "q": "1DvvL80TsnkfuVjfbdhTeOa1Xz0ttq5tQkt33EX3Kvc=",
            "accountId": accountId,
            "sessionId": sessionId,
            "tenantCode": "yongpai"
        }
    )

    if login_result.get("_error"):
        print(f"❌ 登录请求失败：{login_result['_error']}")
        return

    if not login_result.get("success"):
        print(f"❌ 登录失败：{login_result.get('message', login_result)}")
        return

    data = login_result["data"]

    nickName = data["nickName"]
    token = data["token"]
    thirdId = data["thirdId"]
    accountOpenId = data["accountOpenId"]

    print(f"🪪 昵称：{nickName}")

    # 查询积分和兑换次数
    integral_result = request_json(
        "GET",
        f"https://act.tmlyun.com/activity-api/lottery/h5/activity/lottery/userIntegralInfo?activityId={thirdId}",
        headers={
            "Authorization": token,
            "User-Agent": UA,
            "X-TOKEN": "",
            "X-REQUEST-ID": "",
            "Host": "act.tmlyun.com"
        }
    )

    exchangeNum = 0

    if integral_result.get("success"):
        integral_data = integral_result["data"]

        remainIntegral = integral_data["remainIntegral"]
        exchangeNum = integral_data["exchangeNum"]

        print(f"💎 当前积分：{remainIntegral}")
        print(f"🎫 兑换次数：{exchangeNum}")
    else:
        print(f"⚠️ 查询积分返回：{integral_result.get('message', integral_result)}")

    if farmSwitch == 1:
        # 登录农场
        try:
            farm_result = post_form(
                "https://kzsv.cnnb.com.cn/Server/ypfarmapi/?action=client_login",
                {
                    "userId": accountOpenId,
                    "nickname": nickName,
                    "token": sessionId
                },
                farm_headers
            )
        except Exception as e:
            print(f"❌ 农场登录失败：{e}")
            farm_result = {}

        if farm_result.get("code") == 200:
            userinfo = farm_result["data"]["userinfo"]
            treeinfo = farm_result["data"]["treeinfo"]

            farmUserId = userinfo["ID"]
            Level = treeinfo["Level"]
            showLevel = 0 if Level == "-1" else int(Level)

            print(f"🌾 农场ID：{farmUserId}")
            print(f"🌳 种植天数：{showLevel}")

            # 领取种子
            if Level == "-1":
                try:
                    seed_result = post_form(
                        "https://kzsv.cnnb.com.cn/Server/ypfarmapi/?action=client_operation",
                        {
                            "userId": farmUserId,
                            "type": 0,
                            "openId": accountOpenId
                        },
                        farm_headers
                    )

                    if seed_result.get("code") == 200:
                        updateTime = seed_result["data"]["treeinfo"]["UpdateTime"]
                        print(f"🌱 领取种子时间：{updateTime}")
                    else:
                        print(f"🌱 领取种子返回：{seed_result}")
                except Exception as e:
                    print(f"❌ 领取种子失败：{e}")

            # 农场互动
            def farm_interactive(icon, name, type_value):
                try:
                    result = post_form(
                        "https://kzsv.cnnb.com.cn/Server/ypfarmapi/?action=client_interactive",
                        {
                            "userId": farmUserId,
                            "type": type_value
                        },
                        farm_headers
                    )

                    code = result.get("code")

                    if code == 200:
                        print(f"{icon} {name}中")
                    elif code == 501:
                        print(f"{icon} {result.get('data', result)}")
                    elif code == 502:
                        print(f"{icon} 已{name}")
                    else:
                        print(f"{icon} {name}返回：{result}")
                except Exception as e:
                    print(f"{icon} {name}失败：{e}")

            farm_interactive("💧", "浇水", 100)
            farm_interactive("🧪", "施肥", 10)
            farm_interactive("🍃", "除草", 1)

            if showLevel == 7:
                # 果实收获
                try:
                    harvest_result = post_form(
                        "https://kzsv.cnnb.com.cn/Server/ypfarmapi/?action=client_harvest",
                        {
                            "userId": farmUserId
                        },
                        farm_headers
                    )

                    code = harvest_result.get("code")
                    if code == 200:
                        harvest_data = harvest_result.get("data", {})
                        boxinfo = harvest_data.get("boxinfo", [])

                        item_describe = ""
                        if boxinfo and isinstance(boxinfo, list):
                            item_describe = boxinfo[0].get("ItemDescribe", "")

                        if item_describe:
                            print(f"🍎 果实收获成功：{item_describe}")
                        else:
                            print(f"🍎 果实收获成功：{harvest_data}")
                    elif code == 402:
                        print(f"🍎 {harvest_result.get('data', harvest_result)}")
                    elif code == 502:
                        print(f"🍎 果实已收获：{harvest_result.get('msg', harvest_result)}")
                    else:
                        print(f"🍎 果实收获返回：{harvest_result}")
                except Exception as e:
                    print(f"❌ 果实收获失败：{e}")

                # 果实兑换
                try:
                    exchange_fruit_result = post_form(
                        "https://kzsv.cnnb.com.cn/Server/ypfarmapi/?action=client_operation",
                        {
                            "userId": farmUserId,
                            "type": 3,
                            "openId": accountOpenId
                        },
                        farm_headers
                    )

                    code = exchange_fruit_result.get("code")
                    if code == 200:
                        print("🍏 果实兑换成功")
                    elif code == 503:
                        print("🍏 物品数量不足")
                    else:
                        print(f"🍏 果实兑换返回：{exchange_fruit_result}")
                except Exception as e:
                    print(f"❌ 果实兑换失败：{e}")
            else:
                print(f"🍎 种植未到 7 天")
        else:
            print(f"⚠️ 农场登录异常：{farm_result}")

    else:
        print("⏭️ 跳过农场")

    if lotterySwitch == 1:
        # 有兑换次数才兑换抽奖次数并抽奖
        if exchangeNum > 0:
            exchange_result = request_json(
                "GET",
                f"https://act.tmlyun.com/activity-api/lottery/h5/activity/lottery/userExchangeIntegral?activityId={thirdId}&exchangeNum=1",
                headers={
                    "X-TOKEN": "",
                    "Authorization": token,
                    "User-Agent": UA,
                    "X-REQUEST-ID": "",
                    "Host": "act.tmlyun.com"
                }
            )

            if exchange_result.get("message") == "success":
                print("🎫 兑换成功")
            else:
                print(f"🎫 兑换返回：{exchange_result.get('message', exchange_result)}")

            # 抽奖
            lottery_result = request_json(
                "POST",
                "https://act.tmlyun.com/activity-api/lottery/h5/activity/lottery/userActivityLottery",
                headers={
                    "X-TOKEN": "",
                    "Authorization": token,
                    "User-Agent": UA,
                    "X-REQUEST-ID": "",
                    "Content-Type": "application/json",
                    "Host": "act.tmlyun.com"
                },
                json={
                    "activityId": thirdId,
                    "clientId": deviceid,
                    "prizeVersion": 2
                }
            )

            if lottery_result.get("success"):
                lottery_data = lottery_result.get("data", {})

                if lottery_data.get("isPrize") == 0:
                    print("🎰 抽奖结果：谢谢参与")
                else:
                    grade = lottery_data.get("grade", "")
                    print(f"🎰 抽奖结果：{grade}")
            else:
                print(f"🎰 抽奖失败：{lottery_result.get('message', lottery_result)}")
        else:
            print("🎫 无抽奖次数")

        # 钱包登录
        wallet_result = request_json(
            "POST",
            "https://my.tmlyun.com/equity-api/user/auth/userLogin",
            headers={
                "User-Agent": UA,
                "X-REQUEST-ID": "",
                "Content-Type": "application/json",
                "Host": "my.tmlyun.com"
            },
            json={
                "u": "V1IZ/buqnI76J9YZ+wJoTQ==",
                "accountId": accountId,
                "sessionId": sessionId,
            }
        )

        walletToken = ""

        if wallet_result.get("success"):
            wallet_data = wallet_result["data"]
            walletToken = wallet_data["token"]
        else:
            print(f"❌ 钱包登录失败：{wallet_result.get('message', wallet_result)}")

        aliPayTotalPrice = 0
        aliPayBound = False

        # 查询钱包信息
        if walletToken:
            wallet_info_result = request_json(
                "GET",
                f"https://my.tmlyun.com/equity-api/redBag/getWalletInfo?device={deviceid}",
                headers={
                    "X-TOKEN": "",
                    "Authorization": walletToken,
                    "User-Agent": UA,
                    "X-REQUEST-ID": "",
                    "Host": "my.tmlyun.com"
                }
            )

            if wallet_info_result.get("success"):
                wallet_info_data = wallet_info_result["data"][0]

                totalPrice = wallet_info_data["totalPrice"]
                totalTransPrice = wallet_info_data["totalTransPrice"]
                aliPayTotalPrice = wallet_info_data["aliPayTotalPrice"]

                print(f"💵 累计现金：{totalPrice}")
                print(f"🏧 累计提现：{totalTransPrice}")
                print(f"👛 现有现金：{aliPayTotalPrice}")
            else:
                print(f"⚠️ 查询钱包返回：{wallet_info_result.get('message', wallet_info_result)}")

        # 前解绑支付宝、查询/绑定支付宝、提现
        if walletToken:
            alipay_headers = {
                "X-TOKEN": "",
                "Authorization": walletToken,
                "User-Agent": UA,
                "X-REQUEST-ID": "",
                "Host": "my.tmlyun.com"
            }

            if unbindAliPay == 1:
                unbind_result = request_json(
                    "GET",
                    "https://my.tmlyun.com/equity-api/redBag/unBindAliPayAccount",
                    headers=alipay_headers
                )

                if unbind_result.get("message") == "success":
                    print("⛓️‍💥 支付宝解绑成功")
                else:
                    print(f"⛓️‍💥 支付宝解绑返回：{unbind_result.get('message', unbind_result)}")
            else:
                print("⏭️ 跳过支付宝解绑")

            # 查询/绑定支付宝
            bind_result = request_json(
                "GET",
                "https://my.tmlyun.com/equity-api/redBag/getFundsDetail",
                headers=alipay_headers,
                params={"fundsChannelType": 0}
            )

            if bind_result.get("success"):
                bind_data = bind_result.get("data", {})
                realName = bind_data.get("realName", "")
                aliAccount = bind_data.get("account", "")

                if realName or aliAccount:
                    aliPayBound = True
                    print(f"💙 已绑定支付宝：{realName} / {aliAccount}")
                else:
                    if bindAliPay == 1:
                        if userName and account:
                            print("❌ 未绑定支付宝，开始绑定")

                            save_result = request_json(
                                "GET",
                                "https://my.tmlyun.com/equity-api/redBag/saveAliPayAccount",
                                headers=alipay_headers,
                                params={
                                    "userName": userName,
                                    "account": account
                                }
                            )

                            if save_result.get("message") == "success":
                                aliPayBound = True
                                print(f"🔗 绑定成功：{userName} / {account}")
                            else:
                                print(f"🔗 绑定返回：{save_result.get('message', save_result)}")
                        else:
                            print("⏭️ 未配置支付宝绑定")
                    else:
                        print("⏭️ 跳过支付宝绑定")
            else:
                print(f"⚠️ 查询支付宝绑定返回：{bind_result.get('message', bind_result)}")

            # 提现
            if txbindAliPay == 1:
                try:
                    can_trans = float(aliPayTotalPrice) > 0
                except Exception:
                    can_trans = False

                if not aliPayBound:
                    print("🏧 未绑定支付宝")
                elif can_trans:
                    trans_result = request_json(
                        "GET",
                        "https://my.tmlyun.com/equity-api/redBag/createTrans",
                        headers={
                            "X-TOKEN": "",
                            "Authorization": walletToken,
                            "User-Agent": UA,
                            "X-REQUEST-ID": "",
                            "Host": "my.tmlyun.com"
                        },
                        params={
                            "price": aliPayTotalPrice,
                            "fundsChannelType": 0,
                            "yToken": sessionId,
                            "deviceId": deviceid,
                        }
                    )

                    if trans_result.get("message") == "success":
                        print("🏧 提现成功")
                    else:
                        print(f"🏧 提现返回：{trans_result.get('message', trans_result)}")
                else:
                    print("🏧 当前无现金")
            else:
                print("⏭️ 跳过提现")

        # 后解绑支付宝
        if walletToken:
            alipay_headers = {
                "X-TOKEN": "",
                "Authorization": walletToken,
                "User-Agent": UA,
                "X-REQUEST-ID": "",
                "Host": "my.tmlyun.com"
            }

            if hunbindAliPay == 1:
                unbind_result = request_json(
                    "GET",
                    "https://my.tmlyun.com/equity-api/redBag/unBindAliPayAccount",
                    headers=alipay_headers
                )

                if unbind_result.get("message") == "success":
                    print("⛓️‍💥 支付宝解绑成功")
                else:
                    print(f"⛓️‍💥 支付宝解绑返回：{unbind_result.get('message', unbind_result)}")
            else:
                print("⏭️ 跳过支付宝解绑")

        # 查询中奖记录
        prize_record_result = request_json(
            "GET",
            "https://act.tmlyun.com/activity-api/lottery/h5/activity/lottery/accountPrizeRecord/userPrizeRecord",
            headers={
                "X-TOKEN": "",
                "Authorization": token,
                "User-Agent": UA,
                "X-REQUEST-ID": "",
                "Host": "act.tmlyun.com"
            },
            params={
                "activityId": thirdId
            }
        )

        if prize_record_result.get("success"):
            prize_list = prize_record_result.get("data", {}).get("activityAccountPrizeVoList", [])

            global prize_record_text

            print("🎁 中奖记录")
            for item in prize_list[:5]:
                createTime = item.get("createTime", "")
                grade = item.get("grade", "")
                line = f"🕒 {createTime}   ===   🎁 {grade}"
                print(line)
                prize_record_text += line + "\n"
        else:
            print(f"⚠️ 查询中奖记录返回：{prize_record_result.get('message', prize_record_result)}")

    else:
        print("⏭️ 跳过兑换抽奖")

def print_banner():
    print("📮 甬派抽奖")


if __name__ == "__main__":
    accounts = get_env_accounts()
    if not accounts:
        raise SystemExit

    total = len(accounts)
    print_banner()
    print(f"共检测到 {total} 个账号")

    for i, conf in enumerate(accounts, start=1):
        try:
            run_account(i, total, conf)
        except Exception as e:
            print(f"❌ 账号 {i} 执行异常：{e}")

    if lotterySwitch == 1:
        today_total = calc_today_prize_total(prize_record_text)
        today = datetime.now().strftime("%Y-%m-%d")
        total_notice_content = f"{today}\n今日中奖总额：{today_total}元"
        print(f"\n📮 甬派抽奖\n{total_notice_content}")
        send_total_notice(total_notice_content)
    else:
        print("⏭️ 跳过通知")
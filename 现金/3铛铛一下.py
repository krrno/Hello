#cron:33 9,20 * * *
import os
import time
import requests

env_name = "ddyx"
env = os.getenv(env_name)

lottery_id = 6374216

if not env:
    print(f"❌ 未检测到青龙环境变量：{env_name}")
    exit()

accounts = [i.strip() for i in env.strip().splitlines() if i.strip()]

print("""｡ﾟﾟ･｡･ﾟﾟ｡
  ﾟ。  ♡  ｡ﾟ
    ﾟ･｡･ﾟ
   (˶˃ ᵕ ˂˶)
  /づ  ♡ づ""")

print(f"共检测到 {len(accounts)} 个账号")


ua = "Mozilla/5.0 (Linux; Android 13; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/146.0.7680.178 Mobile Safari/537.36 MicroMessenger/8.0.72 MiniProgramEnv/android"


def get_json(url, headers):
    return requests.get(url, headers=headers, timeout=10).json()


for index, account in enumerate(accounts, 1):
    print(f"\n==========🍺账号 {index}/{len(accounts)}🍺==========")

    if "#" not in account:
        print("❌ 账号格式错误，应为：昵称#token")
        continue

    name, token = account.split("#", 1)
    name = name.strip()
    token = token.strip()

    headers = {
        "Host": "vues.dd1x.cn",
        "token": token,
        "content-type": "application/json",
        "charset": "utf-8",
        "Referer": "https://servicewechat.com/wxe378d2d7636c180e/834/page-frame.html",
        "User-Agent": ua
    }

    # 签到
    try:
        sign_url = "https://vues.dd1x.cn/api/v2/sign_join"
        data = get_json(sign_url, headers)

        if data.get("code") == 0:
            sign_msg = data.get("data", {}).get("name", "签到成功")
            print(f"📅 签到: {sign_msg}")
        else:
            print(f"📅 签到: {data.get('msg')}")
    except Exception as e:
        print(f"📅 签到: 请求异常 {e}")

    # 昵称
    print(f"🪪 昵称: {name}")

    # 分享增加抽奖次数
    share_count = 0
    share_url = "https://vues.dd1x.cn/front/activity/add_lottery_count"

    while True:
        try:
            data = get_json(share_url, headers)

            if data.get("code") == 0:
                share_count += 1
                print(f"🔗 分享: 成功 {share_count}次")
                time.sleep(1)
            else:
                print(f"🔗 分享: {data.get('msg')}")
                break
        except Exception as e:
            print(f"🔗 分享: 请求异常 {e}")
            break

    # 抽奖
    lottery_count = 0
    lottery_url = f"https://vues.dd1x.cn/front/activity/update_lottery_result?id={lottery_id}"

    while True:
        try:
            data = get_json(lottery_url, headers)

            if data.get("code") == 0:
                lottery_count += 1
                good_name = data.get("data", {}).get("goodName", "未知奖品")
                print(f"🎉 抽奖{lottery_count}: {good_name}")
                time.sleep(1)
            else:
                print(f"🎉 抽奖: {data.get('msg')}")
                break
        except Exception as e:
            print(f"🎉 抽奖: 请求异常 {e}")
            break

    # 现金
    try:
        cash_url = "https://vues.dd1x.cn/api/h/get_account_detailed"
        data = get_json(cash_url, headers)

        if data.get("code") == 0:
            total = data.get("data", {}).get("total", 0)
            print(f"💰 现金: {total}元")
        else:
            print(f"💰 现金: {data.get('msg')}")
    except Exception as e:
        print(f"💰 现金: 请求异常 {e}")

    time.sleep(1)


print("\n==========🎊执行结束🎊==========")

print("""
｡ﾟﾟ･｡･ﾟﾟ｡
  ﾟ。  ♡  ｡ﾟ
    ﾟ･｡･ﾟ
   (˶×﹏×˶)
  /づ    づ""")
#cron:12 12 * * *
import os
import requests

tokens = os.getenv("jyxe")
if not tokens:
    print("❌ 未检测到环境变量 jyxe")
    exit()

token_list = [t.strip() for t in tokens.splitlines() if t.strip()]

BASE = "https://jiuyixiaoer.fzjingzhou.com/api/Person"

headers = {
    "content-type": "application/x-www-form-urlencoded",
    "platform": "MP-WEIXIN",
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; V2148A Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/146.0.7680.178 Mobile Safari/537.36 XWEB/1460149 MMWEBSDK/20260502 MMWEBID/3317 MicroMessenger/8.0.72.3100(0x28004852) WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64 MiniProgramEnv/android",
    "Host": "jiuyixiaoer.fzjingzhou.com"
}


def post(api, token):
    return requests.post(
        f"{BASE}/{api}",
        headers=headers,
        data={"token": token},
    ).json()


def run(token):
    sign = post("sign", token)
    msg = sign.get("msg", "未知结果")
    print(f"📅 签到: {'签到成功' if msg == 'success' else msg}")

    info = post("index", token)
    data = info.get("data")

    if not data:
        print(f"❌ 查询用户信息失败: {info.get('msg', '未知原因')}")
        return

    print(f'🪪 昵称: {data.get("nickname")}')
    print(f'💰 现金: {data.get("exchange")}元')


def main():
    total = len(token_list)

    print("""｡ﾟﾟ･｡･ﾟﾟ｡
  ﾟ。  ♡  ｡ﾟ
    ﾟ･｡･ﾟ
   (˶˃ ᵕ ˂˶)
  /づ  ♡ づ""")

    print(f"共检测到 {total} 个账号")

    for i, token in enumerate(token_list, 1):
        print(f"\n==========🍺账号 {i}/{total}🍺==========")
        try:
            run(token)
        except Exception as e:
            print(f"❌ 账号 {i} 执行异常: {e}")

    print("\n==========🎊执行结束🎊==========")

    print("""
｡ﾟﾟ･｡･ﾟﾟ｡
  ﾟ。  ♡  ｡ﾟ
    ﾟ･｡･ﾟ
   (˶×﹏×˶)
  /づ    づ""")


if __name__ == "__main__":
    main()
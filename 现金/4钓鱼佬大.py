#钓鱼系列   环境变量 dyxl 格式:openid换行
#cron:*/4 * * * *


import os
import time
import base64
import requests

from concurrent.futures import ThreadPoolExecutor
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


KEY = b"34ef9kcs13sdx823bd1nagf5bmax87s\0"
IV = b"3a64f1kf00l52ecn"

BASE_URL = "https://fishing.fulubro.com/app/api"
PACKAGE = "1"

# 指定昵称不进行提现，按需修改这里
# 示例：SKIP_NAMES = set()   当前没有任何昵称需要跳过提现。
# SKIP_NAMES = {"昵称1"}
# SKIP_NAMES = {"张三", "李四"} 

SKIP_NAMES = {"寸山"}

try:
    from notify import send
except Exception:
    send = None
def make_sign(open_id: str, timestamp: str) -> str:
    raw = f"{timestamp}_{open_id}".encode()
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    encrypted = cipher.encrypt(pad(raw, 16))
    return base64.b64encode(encrypted).decode()
def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "okhttp/4.12.0"})
    return session
def plus_coin_sign(session: requests.Session, open_id: str):
    timestamp = str(int(time.time()))
    return session.post(
        f"{BASE_URL}/plus_coin_sign.php",
        data={
            "userId": open_id,
            "package": PACKAGE,
            "time": timestamp,
            "sign": make_sign(open_id, timestamp),
        },
        timeout=15,
    )
def query_user(session: requests.Session, open_id: str) -> dict:
    return session.get(
        f"{BASE_URL}/my_api.php",
        params={
            "open_id": open_id,
            "package": PACKAGE,
        },
        timeout=15,
    ).json()
def withdraw(session: requests.Session, open_id: str):
    return session.post(
        f"{BASE_URL}/exchange_gold.php?package={PACKAGE}",
        data={
            "type": "money1",
            "openid": open_id,
        },
        timeout=15,
    )
def parse_withdraw_result(text: str):
    text = text.strip()
    if text.startswith("success:"):
        parts = text.split(":")
        amount = ""
        if len(parts) >= 3:
            try:
                amount = f"{int(parts[2]) / 1000:g} 元"
            except Exception:
                amount = parts[2]
        return f"✅ 提现成功: {amount}" if amount else "✅ 提现成功", True, amount
    error_map = {
        "error:余额不足。": "❌ 提现失败: 余额不足",
        "error:两次提现时间必须大于24小时。": "⏳ 提现失败: 两次提现时间必须大于 24 小时",
    }
    if text in error_map:
        return error_map[text], False, ""
    if text.startswith("error:"):
        return f"❌ 提现失败: {text[6:]}", False, ""
    return f"⚠️ 提现未知返回: {text}", False, ""
def run_account(open_id: str, index: int, total: int, skip_names: set[str]):
    open_id = open_id.strip()
    session = get_session()
    logs = [f"\n========== 账号 {index} / {total} =========="]
    notice = None
    try:
        try:
            plus_coin_sign(session, open_id)
        except Exception:
            pass
        info = query_user(session, open_id)
        name = info.get("name", "")
        gold = int(info.get("gold", 0))
        logs.append(f"👤 昵称: {name}")
        logs.append(f"🪙 金币: {gold}")
        if name in skip_names:
            logs.append("⏭️ 跳过提现名单中")
            return "\n".join(logs), notice
        if gold < 1000:
            logs.append(f"⏳ 金币不足: 还差 {1000 - gold}")
            return "\n".join(logs), notice
        result = withdraw(session, open_id).text
        message, success, amount = parse_withdraw_result(result)
        logs.append(message)
        if success:
            notice = f"👤{name} 💰提现成功: {amount}"
    except Exception as e:
        logs.append(f"❌ 账号 {index} 执行异常: {e}")
    return "\n".join(logs), notice
def send_notify(success_notices: list[str]):
    if not success_notices:
        return

    title = "🎣【鱼乐视频】提现通知"
    content = "\n".join(success_notices)

    print("\n========== 青龙通知 ==========")
    print(title)
    print(content)

    if not send:
        print("⚠️ 未找到 notify.py，无法发送青龙通知")
        return
    try:
        send(title, content)
        print("✅ 青龙通知发送成功")
    except Exception as e:
        print(f"❌ 青龙通知发送失败: {e}")
def load_accounts() -> list[str]:
    env = os.getenv("dyxl", "").strip()
    if not env:
        print("❌ 未检测到青龙环境变量 dyxl")
        print("请添加环境变量 dyxl，多账号用回车分隔")
        return []
    return [item.strip() for item in env.splitlines() if item.strip()]
def main():
    accounts = load_accounts()
    if not accounts:
        print("❌ dyxl 环境变量为空")
        return
    total = len(accounts)
    success_notices = []
    print("｡ﾟﾟ･｡･ﾟﾟ｡")
    print("  ﾟ。  ♡  ｡ﾟ")
    print("    ﾟ･｡･ﾟ")
    print("   (˶ᵔ ᵕ ᵔ˶)")
    print("  /づ    づ")
    print(f"共检测到 {total} 个账号")
    if SKIP_NAMES:
        print(f"跳过提现昵称: {', '.join(sorted(SKIP_NAMES))}")
    with ThreadPoolExecutor(max_workers=total) as executor:
        futures = [
            executor.submit(run_account, open_id, index, total, SKIP_NAMES)
            for index, open_id in enumerate(accounts, start=1)
        ]
        for future in futures:
            log, notice = future.result()
            print(log)
            if notice:
                success_notices.append(notice)
    send_notify(success_notices)
if __name__ == "__main__":
    main()
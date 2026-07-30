"""
38 8,20 * * *
众安健康微信小程序 满5元可提现！
抓包ihealth.zhongan.com请求中的Access-Token值和Set-Cookie值
变量名: zajk
变量格式：Access-Token&Cookie
多账号用 @ 符号隔开
cron: 32 7 * * *
青龙面板环境变量示例: export zajk='token1&cookie1@token2&cookie2'
"""
import os
import json
import time
import random
import requests
from datetime import datetime
from typing import Dict, Optional

# ================== 配置项 ==================
NOTIFY = 0          # 0关闭通知，1打开通知
DEBUG = 0           # 0关闭调试，1打开调试

# ================== 辅助函数 ==================
def debug_log(*args):
    if DEBUG:
        print("[DEBUG]", *args)

def random_delay(min_ms: int = 6000, max_ms: int = 8000) -> int:
    """生成随机等待时间（毫秒）"""
    delay = random.randint(min_ms, max_ms)
    print(f"随机等待 {delay}ms")
    time.sleep(delay / 1000)
    return delay


def send_notify(title: str, content: str):
    """发送通知（需自行配置sendNotify模块）"""
    if NOTIFY <= 0:
        print(content)
        return
    try:
        # 尝试导入青龙通知模块
        from sendNotify import send_notify as notify
        notify(title, content)
    except ImportError:
        print(f"未找到通知模块，消息内容：{content}")

# ================== 核心业务类 ==================
class ZAHealth:
    def __init__(self, token_cookie: str, index: int):
        """
        :param token_cookie: 格式 "Access-Token&Cookie"
        :param index: 账号序号
        """
        self.index = index
        parts = token_cookie.strip().split("&")
        if len(parts) < 2:
            raise ValueError(f"账号{index}变量格式错误，应为'Access-Token&Cookie'")
        self.access_token = parts[0]
        self.cookie = parts[1]

        self.session = requests.Session()

        # 基础请求头（不含动态部分）
        self.base_headers = {
            "Host": "ihealth.zhongan.com",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.23(0x1800172f) NetType/WIFI Language/zh_CN",
            "Referer": "https://servicewechat.com/wxbac45cc1588a5a75/210/page-frame.html"
        }

    def _get_headers(self, use_cookie: bool = False) -> Dict:
        """获取请求头，可选是否包含Cookie"""
        headers = self.base_headers.copy()
        headers["Access-Token"] = self.access_token
        if use_cookie:
            headers["Cookie"] = self.cookie
            headers["Origin"] = "https://ihealth.zhongan.com"
            headers["Accept-Language"] = "zh-cn"
            headers["User-Agent"] += " miniProgram/wxbac45cc1588a5a75"
        return headers

    def post_request(self, url: str, body: dict, use_cookie: bool = False) -> Dict:
        """发送POST请求并返回解析后的JSON"""
        try:
            headers = self._get_headers(use_cookie)
            debug_log(f"请求URL: {url}")
            debug_log(f"请求头: {json.dumps(headers, indent=2)}")
            debug_log(f"请求体: {json.dumps(body, indent=2)}")

            resp = self.session.post(url, headers=headers, json=body, timeout=10)
            resp.raise_for_status()

            debug_log(f"响应内容: {resp.text}")

            if resp.text.strip().startswith("{"):
                return resp.json()
            else:
                print(f"非JSON响应: {resp.text[:200]}")
                return {}
        except requests.exceptions.RequestException as e:
            print(f"请求异常: {str(e)}")
            return {}
        except json.JSONDecodeError as e:
            print(f"JSON解析异常: {str(e)}")
            return {}

    def home_page(self) -> Optional[Dict]:
        """获取首页信息"""
        url = "https://ihealth.zhongan.com/api/lemon/v1/common/activity/homePage"
        body = {
            "activityCode": "ONA20220411001",
            "channelCode": "c20195660470001"
        }
        resp = self.post_request(url, body)
        if resp.get("code") == "0":
            return resp
        else:
            print("获取首页信息失败")
            return None

    def sign_in(self) -> bool:
        """签到"""
        url = "https://ihealth.zhongan.com/api/lemon/v1/common/activity/signIn"
        body = {
            "activityCode": "ONA20220411001",
            "channelCode": "c20195660470001"
        }
        resp = self.post_request(url, body)
        if resp.get("code") == "0":
            print("签到成功")
            return True
        else:
            print("签到失败")
            return False

    def do_product_task(self, goods_code: str) -> bool:
        """执行产品推荐任务（浏览商品）"""
        url = "https://ihealth.zhongan.com/api/lemon/v1/applet/mgm/activity/add/award"
        body = {
            "activityCode": "ONA20220411001",
            "channelCode": "1000000004",
            "goodsCode": goods_code,
            "taskId": "110"
        }
        resp = self.post_request(url, body, use_cookie=True)
        if resp.get("code") == "0":
            print(f"商品任务 {goods_code} 完成")
            return True
        else:
            print(f"商品任务 {goods_code} 失败")
            return False

    def process_valuable_rewards(self, reward_list: list) -> None:
        """处理有价奖励（抽奖）"""
        url = "https://ihealth.zhongan.com/api/lemon/v1/common/activity/lottery"
        for reward in reward_list:
            award_id = reward.get("awardDetailId")
            if not award_id:
                continue
            print(f"开始抽奖 ID: {award_id}")
            body = {
                "channelCode": "c20195660470001",
                "activityCode": "ONA20220411001",
                "id": award_id
            }
            resp = self.post_request(url, body)
            if resp.get("code") == "0":
                print(f"抽奖 {award_id} 成功")
            else:
                print(f"抽奖 {award_id} 失败")

    def withdraw(self, amount: int = 500) -> bool:
        """提现（默认5元，单位分）"""
        url = "https://ihealth.zhongan.com/api/lemon/v1/common/activity/withdraw"
        body = {
            "channelCode": "c20195660470001",
            "activityCode": "ONA20220411001",
            "amount": amount
        }
        resp = self.post_request(url, body)
        if resp.get("code") == "0":
            print(f"提现 {amount/100:.2f} 元成功")
            send_notify(f"众安健康已成功提现{amount/100:.2f}元，请前往微信查看！")
            return True
        else:
            print("提现失败")
            return False

    def run(self):
        """主流程"""
        print(f"\n========= 开始【第 {self.index} 个账号】=========\n")

        # 1. 获取首页信息，验证账号有效性
        home = self.home_page()
        if not home:
            return
        random_delay()

        # 2. 签到
        self.sign_in()
        random_delay()

        # 3. 处理产品推荐任务（最多3个）
        product_recommend = home.get("result", {}).get("productRecommend", {})
        product_keys = list(product_recommend.keys())
        for idx, goods_code in enumerate(product_keys[:3], start=1):
            print(f"开始任务{idx}: {goods_code}")
            self.do_product_task(goods_code)
            random_delay()

        # 4. 重新获取首页信息（更新奖励状态）
        home = self.home_page()
        if not home:
            return

        # 5. 处理有价奖励抽奖
        reward_list = home.get("result", {}).get("valuableRewardList", [])
        if reward_list:
            self.process_valuable_rewards(reward_list)
        else:
            print("今日无可领取奖励！明天再试试吧")

        # 6. 提现（可提现金额大于0时）
        sum_allow_withdraw = home.get("result", {}).get("sumAllowWithdraw", 0)
        total_award = home.get("result", {}).get("sumAward", 0)
        print(f"累计金额: {total_award} | 可提现金额: {sum_allow_withdraw}")
        if sum_allow_withdraw > 0:
            # 通常每次提现5元，可根据实际情况调整
            self.withdraw(500)
        else:
            print("无可提现金额")

# ================== 入口函数 ==================
def main():

    # 获取环境变量
    token_str = os.getenv("zajk", "")
    if not token_str:
        print(f"未填写环境变量 zajk")
        return

    # 解析多账号（用 @ 分割）
    accounts = [acc.strip() for acc in token_str.split("@") if acc.strip()]
    for idx, acc in enumerate(accounts, start=1):
        try:
            za = ZAHealth(acc, idx)
            za.run()
        except Exception as e:
            print(f"账号 {idx} 执行异常: {str(e)}")
            import traceback
            traceback.print_exc()
        print("\n")

    print("所有账号执行完毕。")

if __name__ == "__main__":
    main()
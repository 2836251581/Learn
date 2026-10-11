"""
第 2 课 · 实验 B：错误分类 + 指数退避重试（★故意制造失败，看它怎么处理）

学什么：
    1. ★第一原则：**不是所有错误都该重试**（4xx 里只有 429 该重试）
    2. 指数退避 + 随机抖动（jitter）怎么算、为什么必须加抖动
    3. ★SDK 默认自己会重试 2 次 —— 你外包一层就变成 3×3=9 次

跑法（PyCharm）：运行配置选 retry_demo，点 ▶
    命令行等价：..\.venv\Scripts\python.exe retry_demo.py

⚠️ 本脚本会**故意**用错的 key 去撞 401，这是设计好的，不是 bug。
"""

import os
import random
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    OpenAI,
    RateLimitError,
)

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"

# ---------- 重试策略参数 ----------
MAX_ATTEMPTS = 3      # 最多尝试几次
BASE_DELAY = 1.0      # 基础延迟（秒）
MAX_DELAY = 20.0      # 单次延迟封顶


def classify(exc: Exception) -> tuple[str, bool, str]:
    """
    把异常分类 → (类别, 是否该重试, 处理建议)

    ★ 这张分类表是本课核心：
       4xx 里只有 429（限流）该重试；401/403/404/400 重试一万次也没用。
       5xx 和网络类问题才该重试。
    """
    if isinstance(exc, AuthenticationError):
        return "认证失败 401", False, "检查 API Key（★重试无意义，直接退出）"
    if isinstance(exc, NotFoundError):
        return "资源不存在 404", False, "检查模型名是否正确（官方现名 deepseek-flash）"
    if isinstance(exc, BadRequestError):
        return "请求参数错误 400", False, "检查参数（如 max_tokens 是否越界）"
    if isinstance(exc, RateLimitError):
        return "限流 429", True, "配额/频率超限 → 指数退避后重试"
    if isinstance(exc, InternalServerError):
        return "服务端错误 5xx", True, "服务端故障 → 退避重试"
    if isinstance(exc, APITimeoutError):
        return "请求超时", True, "网络慢 → 退避重试"
    if isinstance(exc, APIConnectionError):
        return "连接失败", True, "网络不通/代理问题 → 退避重试"
    if isinstance(exc, APIStatusError):
        status = getattr(exc, "status_code", "?")
        retryable = status in (408, 409, 429) or status >= 500
        return f"HTTP {status}", retryable, "按状态码判断"
    return type(exc).__name__, False, "未知异常，保守起见不重试"


def backoff_delay(attempt: int) -> float:
    """
    指数退避 + 随机抖动。
        attempt=1 → 1s 附近；2 → 2s 附近；3 → 4s 附近（再乘 1~1.5 的抖动）
    为什么加抖动：服务端限流时，如果所有客户端都严格按 1s/2s/4s 重试，
    它们会在同一瞬间一起打过去，把服务端再打垮一次（惊群 thundering herd）。
    """
    delay = BASE_DELAY * (2 ** (attempt - 1))
    delay += random.uniform(0, delay * 0.5)   # ★ 抖动：0 ~ 50%
    return min(delay, MAX_DELAY)


def call_with_retry(client: OpenAI, prompt: str) -> str | None:
    """带分类重试的调用。返回内容，或 None（不可重试的错误 / 用完次数）"""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=60,
            )
            if attempt > 1:
                print(f"  ✅ 第 {attempt} 次尝试成功")
            return resp.choices[0].message.content.strip()

        except Exception as exc:  # noqa: BLE001 —— 生产代码建议窄化捕获范围
            kind, retryable, advice = classify(exc)
            print(f"  ❌ 第 {attempt} 次尝试失败：{kind} —— {advice}")

            if not retryable:
                print("     → ❌ 不可重试的错误，立即放弃（重试只是浪费时间）")
                return None

            if attempt == MAX_ATTEMPTS:
                print(f"     → 已尝试 {MAX_ATTEMPTS} 次，放弃")
                return None

            delay = backoff_delay(attempt)
            print(f"     → 可重试，等待 {delay:.2f} 秒后重试（指数退避 + 抖动）")
            time.sleep(delay)

    return None


def main() -> None:
    load_dotenv()
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    real_key = os.getenv("DEEPSEEK_API_KEY")

    print("=" * 72)
    print("实验 1：错误分类表（本课最该背下来的东西）")
    print("=" * 72)
    table = [
        ("AuthenticationError", "401 认证失败", False, "检查 API Key（★重试无意义）"),
        ("PermissionDeniedError", "403 无权限", False, "检查账号权限/余额"),
        ("NotFoundError", "404 资源不存在", False, "检查模型名（官方现名 deepseek-flash）"),
        ("BadRequestError", "400 参数错误", False, "检查参数（如 max_tokens 越界）"),
        ("RateLimitError", "429 限流", True, "★配额/频率超限 → 指数退避重试"),
        ("InternalServerError", "5xx 服务端故障", True, "★退避重试"),
        ("APITimeoutError", "请求超时", True, "★退避重试"),
        ("APIConnectionError", "网络连接失败", True, "★退避重试（注意代理！）"),
    ]
    print(f"  {'异常类':<24}{'含义':<18}{'该重试':<8}处理建议")
    print("  " + "-" * 86)
    for name, meaning, retryable, advice in table:
        flag = "✅ 是" if retryable else "❌ 否"
        print(f"  {name:<24}{meaning:<18}{flag:<8}{advice}")
    print("\n  ★ 口诀：**4xx 里只有 429 该重试**；5xx 和网络类才该重试。")

    print()
    print("=" * 72)
    print("实验 2：真的撞一次 401（故意的，看它会不会傻乎乎重试）")
    print("=" * 72)
    bad_client = OpenAI(api_key="sk-00000000000000000000000000000000",
                        base_url=BASE_URL, max_retries=0)
    call_with_retry(bad_client, "你好")

    print()
    print("=" * 72)
    print("实验 3：用正确的 key 正常调用（对比：走成功路径）")
    print("=" * 72)
    if real_key:
        good_client = OpenAI(api_key=real_key, base_url=BASE_URL, max_retries=0)
        answer = call_with_retry(good_client, "用一句话解释什么是「指数退避」")
        print(f"  ✅ 回答：{answer}")
    else:
        print("  （没找到 key，跳过）")

    print()
    print("=" * 72)
    print("实验 4：退避延迟长什么样（含抖动，所以每次都不一样）")
    print("=" * 72)
    for attempt in (1, 2, 3, 4):
        samples = [f"{backoff_delay(attempt):.2f}s" for _ in range(3)]
        print(f"  第 {attempt} 次重试：等待 {' / '.join(samples)}（跑三次看抖动范围）")

    print()
    print("=" * 72)
    print("★ 两个必须记住的点")
    print("=" * 72)
    print("""
1. 4xx 里只有 429 该重试。401/403/404/400 重试一万次也没用，
   只会白烧时间、还可能把自己的配额耗光。

2. `openai` SDK **默认自己会重试 2 次**（针对连接错误/429/5xx）。
   你在外面再包一层重试，实际请求次数是乘法关系（3 × 3 = 9 次）。
   本脚本用 `max_retries=0` 显式关掉，让每一次尝试都看得见 ——
   要么关掉自己接管，要么清楚知道有几层，别糊里糊涂叠重试。
""")


if __name__ == "__main__":
    main()

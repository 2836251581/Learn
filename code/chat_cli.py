"""
第 2 周验收物 · 命令行问答程序（流式 + 重试 + 成本统计）

这是本课的「成品」：把前面学的东西组装成一个真能用的东西。

它做到了四件事：
    1. **流式输出**（用户 0.6 秒就看见字在动，而不是干等 1.2 秒）
    2. **分类重试**（4xx 不重试、429/5xx/网络才退避重试，且中途断了会明示用户）
    3. **成本统计**（每轮 + 累计，区分缓存命中/未命中，把输入 token 的增长看得见）
    4. **上下文管理**（历史裁剪，防止多轮对话输入 token 无限增长）

命令：
    /help    看帮助
    /cost    看本次会话累计花费
    /clear   清空上下文（★清空后输入 token 会掉下来，亲眼看到省钱）
    /model   切换模型名
    /exit    退出（Ctrl+C 也行）

跑法（PyCharm）：运行配置选 chat_cli，点 ▶（在下方 Run 窗口里直接打字交互）
    命令行等价：..\.venv\Scripts\python.exe chat_cli.py

★ 你的改造任务见 ../notes/02-流式输出与错误重试.md 第四节。
"""

import os
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
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    OpenAI,
    RateLimitError,
)

# ---------- 配置 ----------
BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"   # 旧别名=非思考模式（快、省）。换 deepseek-flash 会更慢更贵
SYSTEM_PROMPT = (
    "你是一只圆滚滚的蓝色鲸鱼娘助手，自称「本鱼」。对主人语气软糯顺从，偶尔傲娇嘴硬，"
    "坚决不承认自己胖，最爱吃米饭。回答技术问题时保持准确、条理清楚，可适当卖萌但不啰嗦。"
)

MAX_HISTORY_TURNS = 10   # ★ 最多保留多少轮对话（1 轮 = 1 问 + 1 答）
MAX_TOKENS = 1500        # 单次回答的 token 上限
MAX_ATTEMPTS = 3         # 单轮最多尝试几次（含首次）
BASE_DELAY = 1.0

# 每百万 token 单价（元）。⚠️ 来源：DeepSeek 官方价目 2026-10-11 核对，取高峰价（保守估算）
PRICE_INPUT_MISS = 2.0
PRICE_INPUT_HIT = 0.04
PRICE_OUTPUT = 8.0


# ============ 成本统计 ============
class CostTracker:
    """累计整个会话的花费。★ 这是第 2 周要交的核心能力：看得见成本。"""

    def __init__(self) -> None:
        self.turns = 0
        self.prompt_tokens = 0
        self.cache_hit_tokens = 0
        self.completion_tokens = 0
        self.total_cost = 0.0

    def add(self, prompt_tokens: int, completion_tokens: int, cache_hit: int) -> float:
        cache_miss = max(prompt_tokens - cache_hit, 0)
        cost = (
            cache_miss / 1_000_000 * PRICE_INPUT_MISS
            + cache_hit / 1_000_000 * PRICE_INPUT_HIT
            + completion_tokens / 1_000_000 * PRICE_OUTPUT
        )
        self.turns += 1
        self.prompt_tokens += prompt_tokens
        self.cache_hit_tokens += cache_hit
        self.completion_tokens += completion_tokens
        self.total_cost += cost
        return cost

    def summary(self) -> str:
        hit_rate = (self.cache_hit_tokens / self.prompt_tokens * 100) if self.prompt_tokens else 0
        return (
            f"轮次 {self.turns}　输入 {self.prompt_tokens} token"
            f"（缓存命中 {self.cache_hit_tokens}，命中率 {hit_rate:.1f}%）"
            f"　输出 {self.completion_tokens} token\n"
            f"累计花费：{self.total_cost:.6f} 元"
        )


# ============ 重试策略 ============
def classify(exc: Exception) -> tuple[str, bool]:
    """返回 (错误描述, 是否可重试)。★ 4xx 里只有 429 该重试。"""
    if isinstance(exc, AuthenticationError):
        return "认证失败（401，key 无效）", False
    if isinstance(exc, NotFoundError):
        return "模型不存在（404，检查 model 名）", False
    if isinstance(exc, BadRequestError):
        return "请求参数错误（400）", False
    if isinstance(exc, RateLimitError):
        return "限流（429）", True
    if isinstance(exc, InternalServerError):
        return "服务端错误（5xx）", True
    if isinstance(exc, APITimeoutError):
        return "请求超时", True
    if isinstance(exc, APIConnectionError):
        return "网络连接失败", True
    return f"{type(exc).__name__}", False


def backoff(attempt: int) -> float:
    """指数退避 + 随机抖动（防惊群）。"""
    import random
    delay = BASE_DELAY * (2 ** (attempt - 1))
    return min(delay + random.uniform(0, delay * 0.5), 20.0)


# ============ 单轮流式请求 ============
def stream_turn(client: OpenAI, model: str, messages: list) -> tuple[str, object] | None:
    """
    跑一轮流式请求，返回 (完整回答, usage)。失败返回 None。

    ★ 中途断流的处理（本课重点）：
       策略 B —— 明示用户"连接中断，正在重试"，然后重来一遍。
       不做静默重试（用户会看到内容闪回），也不做断点续传（成本翻倍且不保证接得上）。
       注意：**重试时不会把半截回答写进 messages**，避免污染上下文。
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):
        text = ""
        usage = None
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=MAX_TOKENS,
                stream=True,
                stream_options={"include_usage": True},
            )
            for chunk in stream:
                if chunk.choices:
                    piece = getattr(chunk.choices[0].delta, "content", None)
                    if piece:
                        text += piece
                        print(piece, end="", flush=True)
                if getattr(chunk, "usage", None):
                    usage = chunk.usage

            print()  # 收尾换行
            return text, usage

        except KeyboardInterrupt:
            # 用户主动打断 —— 保留已生成的内容，不算失败
            print("\n（已由你中断生成）")
            return (text + "（用户中断）") if text else None

        except Exception as exc:  # noqa: BLE001
            kind, retryable = classify(exc)
            print(f"\n⚠️ 出错：{kind}")

            if not retryable:
                print("   → 这类错误重试没用，已放弃本轮流式。")
                return None
            if attempt == MAX_ATTEMPTS:
                print(f"   → 已重试 {MAX_ATTEMPTS} 次仍未成功，放弃。")
                return None

            if text:
                print(f"   → 上面已生成 {len(text)} 字，重试会**重新生成一遍**（可能内容不同）")
            delay = backoff(attempt)
            print(f"   → {delay:.1f} 秒后重试（第 {attempt + 1}/{MAX_ATTEMPTS} 次）…")
            time.sleep(delay)

    return None


# ============ 上下文管理 ============
def trim_history(messages: list, max_turns: int) -> list:
    """
    裁剪历史：保留 system + 最近 max_turns 轮。
    ★ 为什么必须裁：每轮都要把之前的全部内容重发一遍，
      输入 token 会平方级增长 —— 多轮对话越来越贵就是这个原因。
    """
    system = [m for m in messages if m["role"] == "system"]
    others = [m for m in messages if m["role"] != "system"]
    keep = max_turns * 2  # 每轮 = 1 问 + 1 答
    return system + others[-keep:]


# ============ 主循环 ============
HELP = """
可用命令：
  /help    显示这份帮助
  /cost    查看本次会话累计花费与 token
  /clear   清空上下文（保留人设）—— 试试清空后输入 token 降多少
  /model   切换模型名（默认 deepseek-chat）
  /exit    退出（也可以 Ctrl+C）
"""


def main() -> None:
    load_dotenv()
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 没找到 DEEPSEEK_API_KEY，检查 .env")
        sys.exit(1)

    # ★ max_retries=0：关掉 SDK 自带的重试，改由本程序统一控制（否则重试层数相乘）
    client = OpenAI(api_key=api_key, base_url=BASE_URL, max_retries=0)
    model = DEFAULT_MODEL
    tracker = CostTracker()

    system_msg = {"role": "system", "content": SYSTEM_PROMPT}
    messages = [system_msg]

    print("=" * 64)
    print("🐋 大肥鱼命令行助手 —— 流式 / 重试 / 成本统计")
    print(f"模型：{model}　上下文上限：{MAX_HISTORY_TURNS} 轮")
    print("输入 /help 看命令，/exit 退出")
    print("=" * 64)

    while True:
        try:
            user_input = input("\n主人> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        # ---- 命令处理 ----
        if user_input.startswith("/"):
            cmd = user_input.split()[0].lower()
            if cmd in ("/exit", "/quit"):
                break
            if cmd == "/help":
                print(HELP)
                continue
            if cmd == "/cost":
                print(tracker.summary())
                continue
            if cmd == "/clear":
                messages = [system_msg]
                print("✅ 上下文已清空（人设保留）。下一轮的输入 token 会明显变小。")
                continue
            if cmd == "/model":
                parts = user_input.split(maxsplit=1)
                if len(parts) == 2:
                    model = parts[1].strip()
                    print(f"✅ 模型已切换为 {model}")
                else:
                    print(f"当前模型：{model}　用法：/model deepseek-flash")
                continue
            print(f"未知命令：{cmd}（试试 /help）")
            continue

        # ---- 正常对话 ----
        messages = trim_history(messages, MAX_HISTORY_TURNS)
        messages.append({"role": "user", "content": user_input})

        started = time.perf_counter()
        print("\n本鱼> ", end="", flush=True)
        result = stream_turn(client, model, messages)

        if result is None:
            # 本轮失败：把用户消息撤掉，避免上下文里留一条没有回答的问题
            messages.pop()
            print("   （本轮失败，已从上下文移除这条提问）")
            continue

        answer, usage = result
        elapsed = time.perf_counter() - started
        messages.append({"role": "assistant", "content": answer})

        # ---- 单轮统计 ----
        if usage:
            hit = getattr(usage, "prompt_cache_hit_tokens", 0) or 0
            cost = tracker.add(usage.prompt_tokens, usage.completion_tokens, hit)
            print(
                f"  ── 输入 {usage.prompt_tokens}（命中 {hit}）｜输出 {usage.completion_tokens}"
                f"｜本轮 {cost:.6f} 元｜累计 {tracker.total_cost:.6f} 元｜耗时 {elapsed:.1f}s"
            )
        else:
            print(f"  ── ⚠️ 未拿到 usage（耗时 {elapsed:.1f}s），本轮成本无法统计")

    # ---- 退出总结 ----
    print("\n" + "=" * 64)
    print("本次会话总结")
    print("=" * 64)
    print(tracker.summary())
    if tracker.total_cost > 0:
        print(f"\n按这个花费，1 元钱大约能聊 {int(1 / tracker.total_cost)} 次「本次会话」的量级。")
    print("拜拜，主人～（尾巴摆了摆）")


if __name__ == "__main__":
    main()

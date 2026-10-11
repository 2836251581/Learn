"""
第 2 课 · 实验 A：流式输出最小实现 + TTFT / TPS 测量

学什么：
    1. 流式和非流式在代码上差在哪（delta vs message）
    2. `stream_options={"include_usage": True}` 为什么必须有
    3. 怎么测 TTFT（首字延迟）和 TPS（每秒 token 数）—— 这两个指标决定了"感觉快不快"

跑法（PyCharm）：运行配置选 stream_demo，点 ▶
    命令行等价：..\.venv\Scripts\python.exe stream_demo.py

★ 改造任务：把 MAX_TOKENS 调大、把 QUESTION 换成你感兴趣的问题，观察 TPS 变化。
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
from openai import OpenAI

# ---------- 配置区（★ 模型名抽成常量，改一处就够）----------
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"  # 旧别名=非思考模式；换 deepseek-flash 会默认开思考模式（更慢更贵）
QUESTION = "用五句话解释什么是「向量检索」，假设读者是刚学编程的大学生。"
MAX_TOKENS = 400

# 每百万 token 单价（元）。⚠️ 来源：DeepSeek 官方价目，2026-10-11 核对，取高峰价（保守）
PRICE_INPUT_MISS_PER_M = 2.0    # 未命中缓存的输入
PRICE_INPUT_HIT_PER_M = 0.04    # 命中缓存的输入（约为未命中的 1/50）
PRICE_OUTPUT_PER_M = 8.0


def estimate_cost(prompt_tokens: int, completion_tokens: int, cache_hit: int = 0) -> float:
    """按命中/未命中分别计价 —— 这就是为什么必须拿到 cache_hit 字段。"""
    cache_miss = max(prompt_tokens - cache_hit, 0)
    return (
        cache_miss / 1_000_000 * PRICE_INPUT_MISS_PER_M
        + cache_hit / 1_000_000 * PRICE_INPUT_HIT_PER_M
        + completion_tokens / 1_000_000 * PRICE_OUTPUT_PER_M
    )


def stream_answer(client: OpenAI, question: str) -> None:
    """流式输出答案，并统计 TTFT / TPS / 成本。"""
    started = time.perf_counter()
    first_token_at = None
    text = ""
    chunk_count = 0
    usage = None

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "你是技术讲解员，讲解准确、简洁，多用类比。"},
            {"role": "user", "content": question},
        ],
        max_tokens=MAX_TOKENS,
        stream=True,  # ★ 关键开关 1
        stream_options={"include_usage": True},  # ★ 关键开关 2：不加就拿不到 usage
    )

    for chunk in stream:
        chunk_count += 1

        # ★ 坑：最后一个 chunk 的 choices 是[]（只带 usage），必须先判空
        if chunk.choices:
            delta = chunk.choices[0].delta
            piece = getattr(delta, "content", None)  # ★ 是 delta，不是 message
            if piece:  # ★ 坑：delta.content 可能是 None
                if first_token_at is None:
                    first_token_at = time.perf_counter()
                text += piece
                print(piece, end="", flush=True)  # flush 必须加，否则不是逐字显示

        # usage 只在最后一个 chunk 上出现
        if getattr(chunk, "usage", None):
            usage = chunk.usage

    finished = time.perf_counter()

    # ---------- 统计 ----------
    print("\n" + "─" * 60)
    ttft = (first_token_at - started) if first_token_at else float("nan")
    total = finished - started
    print(f"收到的 chunk 数：{chunk_count}")
    print(f"★ TTFT（首字延迟）：{ttft:.2f} 秒")
    print(f"★ 总耗时：{total:.2f} 秒")

    if usage:
        ct = usage.completion_tokens
        hit = getattr(usage, "prompt_cache_hit_tokens", 0) or 0
        tps = ct / (finished - first_token_at) if first_token_at and finished > first_token_at else 0
        # TPS 从「第一个字出现」开始算，才是真正的生成速度
        print(f"★ 生成速度 TPS：{tps:.1f} token/秒")
        print(f"输入 token：{usage.prompt_tokens}（缓存命中 {hit} / 未命中 {usage.prompt_tokens - hit}）")
        print(f"输出 token：{ct}")
        print(f"本次花费约：{estimate_cost(usage.prompt_tokens, ct, hit):.6f} 元")
    else:
        print("⚠️ 没拿到 usage —— 检查是否漏了 stream_options")

    print(f"\n总字数：{len(text)}")


def main() -> None:
    load_dotenv()
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 没找到 DEEPSEEK_API_KEY")
        sys.exit(1)

    # 关掉 SDK 自动重试，让本脚本的观测更干净（本课实验 B 会专门讲重试）
    client = OpenAI(api_key=api_key, base_url=BASE_URL, max_retries=0)

    print(f"问题：{QUESTION}\n")
    print("=" * 60)
    stream_answer(client, QUESTION)
    print("=" * 60)
    print("\n★ 试试：把 MAX_TOKENS 调大 / 换个问题，看 TTFT 和 TPS 会不会变。")
    print("  提示：TTFT 主要受「首字生成」影响，TPS 受模型负载和输出长度影响。")


if __name__ == "__main__":
    main()

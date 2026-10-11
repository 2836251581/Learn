"""
附加实验：temperature=0 到底可不可复现？为什么本鱼和主人的结果不一样？

背景（2026-10-11 真实争议）：
    本鱼跑 run_experiments.py，temperature=0.0 两遍输出不同（鲸语汐/蓝汐/鲸小灵 vs 鲸语/汐音/澜心）
    主人跑同一个脚本，temperature=0.0 两遍完全相同（鲸语/汐音/澜心 两次一样）
    → 谁对？还是「有时一样、有时不一样」？

这个脚本专门查清楚，思路：
    1. 同一个 prompt 用 temperature=0 连跑 6 次，数一数有几种不同结果
    2. 每次都打印 usage 里的缓存命中字段（DeepSeek 返回 prompt_cache_hit_tokens / miss）
       —— 因为「结果完全相同」有可能是**服务端缓存**造成的，而不是真的确定性
    3. 全程用同一个 client、同一个 prompt，排除其他变量

跑法（PyCharm 里选 run_config_repeat_test 运行配置，点 ▶）：
    ..\.venv\Scripts\python.exe run_config_repeat_test.py
"""

import os
import sys
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

from dotenv import load_dotenv
from openai import OpenAI

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"

QUESTION = "给一个鲸鱼娘 AI 助手起 3 个中文名字，每行一个，只写名字不要解释。"
SYSTEM_PROMPT = "你是一个起名助手。只输出名字，不要任何解释和标点。"

REPEAT = 6  # 跑 6 次，样本够看出规律


def main() -> None:
    load_dotenv()
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=BASE_URL)

    print(f"模型：{MODEL}　temperature = 0.0　连续跑 {REPEAT} 次")
    print(f"问题：{QUESTION}")
    print("=" * 72)

    answers = []
    for i in range(1, REPEAT + 1):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": QUESTION},
            ],
            temperature=0.0,
            max_tokens=300,
        )
        text = resp.choices[0].message.content.strip()
        answers.append(text)

        # ★ 缓存字段：DeepSeek 命中缓存时会便宜很多，也可能让输出「看起来」完全一致
        u = resp.usage
        hit = getattr(u, "prompt_cache_hit_tokens", None)
        miss = getattr(u, "prompt_cache_miss_tokens", None)
        cache_info = f"缓存命中 {hit} / 未命中 {miss}" if hit is not None else "（此接口未返回缓存字段）"

        print(f"\n第 {i} 次：{text.replace(chr(10), ' / ')}")
        print(f"        输入 {u.prompt_tokens} / 输出 {u.completion_tokens} token　{cache_info}")

    print("\n" + "=" * 72)
    print("★ 结论统计")
    print("=" * 72)
    counter = Counter(answers)
    print(f"跑了 {REPEAT} 次，出现 {len(counter)} 种不同结果：\n")
    for text, n in counter.most_common():
        print(f"  {n} 次  {text.replace(chr(10), ' / ')}")

    if len(counter) == 1:
        print("\n→ 本次实验：temperature=0 完全可复现（6/6 一模一样）")
        print("  可能原因：服务端缓存命中，或采样确实收敛到同一个高概率路径")
    else:
        print(f"\n→ 本次实验：temperature=0 **不可复现**（{len(counter)} 种结果）")
        print("  结论：temperature=0 只是「几乎确定」，不是「完全确定」")

    print("\n⚠️ 重要提醒：这只是一次实验的结果。")
    print("   要下结论，必须多次运行本脚本，看结论会不会翻转 —— 这正是第 7 周做评测集要面对的问题。")


if __name__ == "__main__":
    main()

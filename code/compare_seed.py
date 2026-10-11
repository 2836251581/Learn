"""
第 1 课 · 进阶挑战：seed 参数能不能把 temperature=0 的抖动钉死？

背景：
    我们已经实测：temperature=0 时主答案概率极高，但偶尔会抖（6 次里可能抖 1 次）。
    那能不能靠 `seed` 参数强制复现？本脚本就是来验这个的。

实验设计（三组对照，这是重点）：
    A 组：不加 seed，同一个 prompt 跑 4 次   → 看自然抖动
    B 组：加 seed=42，跑 4 次               → 看是否完全一致
    C 组：加 seed=42，但**换一个 prompt**    → 验证「seed 是不是和 prompt 绑定的」

跑法（PyCharm 里选 compare_seed 运行配置，点 ▶）：
    ..\.venv\Scripts\python.exe compare_seed.py

★ 重要的不是结果，是你要回答三个问题：
    1. 加了 seed 之后，B 组 4 次真的一模一样吗？
    2. seed 相同但 prompt 不同（C 组），输出会和 B 组一样吗？为什么？
    3. 如果 seed 不能保证复现，做评测时还能靠什么？（翻回第 1 课找答案）
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

SYSTEM_PROMPT = "你是一个起名助手。只输出名字，不要任何解释和标点。"
QUESTION_A = "给一个鲸鱼娘 AI 助手起 3 个中文名字，每行一个，只写名字不要解释。"
QUESTION_B = "给一个猫娘 AI 助手起 3 个中文名字，每行一个，只写名字不要解释。"

SEED = 42
REPEAT = 4


def ask(client: OpenAI, question: str, seed=None) -> dict:
    """发一次请求。seed=None 时不传 seed 参数。"""
    kwargs = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        "temperature": 0.0,
        "max_tokens": 300,
    }
    if seed is not None:
        kwargs["seed"] = seed

    try:
        resp = client.chat.completions.create(**kwargs)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    return {
        "ok": True,
        "text": resp.choices[0].message.content.strip(),
        "prompt_tokens": resp.usage.prompt_tokens,
        "completion_tokens": resp.usage.completion_tokens,
    }


def run_group(client: OpenAI, title: str, question: str, seed=None) -> list:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")
    results = []
    for i in range(1, REPEAT + 1):
        r = ask(client, question, seed=seed)
        if not r["ok"]:
            print(f"  第 {i} 次 ❌ {r['error']}")
            if "seed" in r["error"].lower() or "unsupported" in r["error"].lower():
                print("  ⚠️ 看起来这个平台/模型**不接受 seed 参数** —— 这本身就是重要结论！")
                print("     请去 DeepSeek 官方文档确认：seed 到底支持不支持？")
            results.append(None)
            continue
        results.append(r["text"])
        print(f"  第 {i} 次：{r['text'].replace(chr(10), ' / ')}   （{r['completion_tokens']} token）")

    valid = [x for x in results if x]
    if valid:
        print(f"  → 这组跑出 {len(set(valid))} 种不同结果")
    return valid


def main() -> None:
    load_dotenv()
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 没找到 DEEPSEEK_API_KEY")
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=BASE_URL)

    a = run_group(client, "A 组：不加 seed（对照组，看自然抖动）", QUESTION_A, seed=None)
    b = run_group(client, f"B 组：加 seed={SEED}（同一 prompt）", QUESTION_A, seed=SEED)
    c = run_group(client, f"C 组：加 seed={SEED}（换了 prompt）", QUESTION_B, seed=SEED)

    print("\n" + "=" * 72)
    print("★ 汇总对照")
    print("=" * 72)
    for name, group in [("A 不加 seed", a), ("B 加 seed 同 prompt", b), ("C 加 seed 换 prompt", c)]:
        if group:
            print(f"{name:<22} 跑 {len(group)} 次 → {len(set(group))} 种结果"
                  f"{'（完全一致 ✅）' if len(set(group)) == 1 else '（仍有抖动 ⚠️）'}")

    print("\n★ 请回答这三个问题（写进笔记里）：")
    print("  1. 加 seed 后 B 组真的一样吗？")
    print("  2. C 组换了 prompt，输出和 B 组相同吗？seed 到底绑定的是什么？")
    print("  3. 如果 seed 不可靠，评测该怎么保证可比性？")


if __name__ == "__main__":
    main()

"""
第 1 课实验：temperature 到底改变了什么？

同一个问题，用三个不同的 temperature 各跑一次，打印输出和成本。

跑法（在 code 目录下）：
    ..\.venv\Scripts\python.exe run_experiments.py

读代码时注意两件事：
    1. 怎么复用 estimate_cost —— 功能拆成函数，才能被多处调用（工程习惯）
    2. 循环里只改了 temperature 一个变量 —— 这叫「控制变量」
       想验证「是不是 temperature 造成的差异」，就必须只动它一个。
"""

import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

try:
    from dotenv import load_dotenv
    from openai import OpenAI
except ModuleNotFoundError as exc:
    print(f"❌ 缺少依赖：{exc.name}，请先跑 pip install -r requirements.txt")
    sys.exit(1)

# ---------- 配置区 ----------
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"

# 每百万 token 单价（元）。⚠️ 以平台官网最新价目为准，这里只是估算。
PRICE_INPUT_PER_M = 2.0
PRICE_OUTPUT_PER_M = 8.0

# ★ 实验变量：只改 temperature
# 为什么用 [0.0, 1.1] 而不是中庸的 0.7？
#   因为要看「差异」，就要把两端拉开 —— 实验设计的第一原则。
TEMPERATURES = [0.0, 1.1]

# ★ 任务要选「开放式」的（创意、命名、头脑风暴），随机性才看得出来。
#   如果你问「什么是 RAG」这种有标准答案的问题，三种温度输出几乎一样 —— 那是任务选错了，不是 temperature 没用。
QUESTION = "给一个鲸鱼娘 AI 助手起 3 个中文名字，每行一个，只写名字不要解释。"

SYSTEM_PROMPT = "你是一个起名助手。只输出名字，不要任何解释和标点。"

# ★ 每个温度跑几遍？
#   跑 2 遍是为了验证一个关键问题：temperature=0 是不是真的「每次都一样」。
#   只跑一遍看不出可复现性 —— 这是实验设计的基本功。
REPEATS = 2


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """按单价粗略估算本次花费（元）。"""
    return (
        prompt_tokens / 1_000_000 * PRICE_INPUT_PER_M
        + completion_tokens / 1_000_000 * PRICE_OUTPUT_PER_M
    )


def run_once(client: OpenAI, temperature: float) -> dict:
    """跑一次调用，返回这一轮的结果（不打印，只算）—— 便于以后改成批量统计。"""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": QUESTION},
        ],
        temperature=temperature,
        max_tokens=300,
    )
    usage = resp.usage
    return {
        "temperature": temperature,
        "answer": resp.choices[0].message.content.strip(),
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "cost": estimate_cost(usage.prompt_tokens, usage.completion_tokens),
    }


def main() -> None:
    load_dotenv()
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 没找到 DEEPSEEK_API_KEY，请检查 .env 文件")
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=BASE_URL)

    print(f"实验问题：{QUESTION}")
    print(f"模型：{MODEL}　实验变量：temperature = {TEMPERATURES}　每个温度跑 {REPEATS} 遍")
    print("=" * 70)

    results = []
    for t in TEMPERATURES:
        for i in range(1, REPEATS + 1):
            print(f"\n▶ temperature = {t}　第 {i}/{REPEATS} 遍")
            try:
                r = run_once(client, t)
            except Exception as exc:  # noqa: BLE001
                print(f"  ❌ 失败：{type(exc).__name__}: {exc}")
                continue
            r["run"] = i
            results.append(r)
            print(f"  {r['answer'].replace(chr(10), ' / ')}")
            print(
                f"  『输入 {r['prompt_tokens']} / 输出 {r['completion_tokens']} token，"
                f"花费约 {r['cost']:.6f} 元』"
            )

    if not results:
        print("\n全部失败，检查网络或 key。")
        return

    # ---------- 汇总 ----------
    total_cost = sum(r["cost"] for r in results)
    total_tokens = sum(r["prompt_tokens"] + r["completion_tokens"] for r in results)

    print("\n" + "=" * 70)
    print("实验汇总")
    print("=" * 70)
    print(f"{'temperature':>12} | {'遍':>3} | {'输入':>6} | {'输出':>6} | {'花费(元)':>10}")
    print("-" * 70)
    for r in results:
        print(
            f"{r['temperature']:>12} | {r['run']:>3} | {r['prompt_tokens']:>6} | "
            f"{r['completion_tokens']:>6} | {r['cost']:>10.6f}"
        )
    print("-" * 70)

    # ★ 关键统计：每个温度下，几次输出里有几个「不一样」的
    print("\n★ 可复现性统计（这是本实验真正的结论）")
    for t in TEMPERATURES:
        answers = [r["answer"] for r in results if r["temperature"] == t]
        if not answers:
            continue
        distinct = len(set(answers))
        verdict = "完全一致（可复现）" if distinct == 1 else f"有 {distinct} 种不同结果（随机）"
        print(f"  temperature={t}：跑了 {len(answers)} 遍 → {verdict}")

    print(f"\n三次共 {total_tokens} token，总花费约 {total_cost:.6f} 元")
    print(f"平均单次 {total_cost / len(results):.6f} 元")
    print(
        "\n★ 自己再想三个问题：\n"
        "  1. 为什么「什么是 RAG」这种问题看不出温度差异，而起名就能看出来？\n"
        "  2. 如果做 RAG 评测集（第 7 周要做的），应该用哪个 temperature？为什么？\n"
        "  3. temperature=0 两次输出真的一字不差吗？如果差了一点，差在哪？"
    )


if __name__ == "__main__":
    main()

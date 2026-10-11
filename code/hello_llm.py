"""
第一个大模型程序 —— 跑通它，你的 AI 学习之路就正式开始。

准备：
    1. 装依赖：pip install openai python-dotenv
    2. 在同目录建 .env 文件，写入：
           DEEPSEEK_API_KEY=你的key
    3. 确认 .gitignore 里有 .env（否则你的 key 会被爬虫扫到盗刷）

运行：
    python hello_llm.py

说明：
    - 这里用 DeepSeek 举例，因为它便宜、中文好、接口兼容 OpenAI 格式。
    - 换其他平台（通义千问 / 智谱 / 硅基流动 / 月之暗面）只需改 base_url 和 model 名，
      因为国内主流平台都兼容同一套接口协议。这就是为什么第一步学 openai 这个 SDK。
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    from openai import OpenAI
except ModuleNotFoundError as exc:
    missing = exc.name
    print(f"❌ 缺少依赖：{missing}")
    print()
    print("请先安装依赖（在当前目录执行）：")
    print("    pip install -r requirements.txt")
    print()
    print("如果下载很慢，先换国内源（见 ../开局配置.md 步骤 1）：")
    print("    python -m pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple")
    sys.exit(1)

# ---------- 配置区：换平台只改这两行 ----------
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"
# ---------------------------------------------

# 每百万 token 的大致价格（元），用于估算花费。具体以平台官网为准。
# DeepSeek 会返回缓存命中情况，这里做粗略估算。
PRICE_INPUT_PER_M = 2.0
PRICE_OUTPUT_PER_M = 8.0


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """粗略估算本次调用花费（元）。养成看成本的习惯，这是工程思维的一部分。"""
    return (
        prompt_tokens / 1_000_000 * PRICE_INPUT_PER_M
        + completion_tokens / 1_000_000 * PRICE_OUTPUT_PER_M
    )


def main() -> None:
    # 先读当前目录的 .env，再补读上一级的（key 放在哪一层都能找到）
    load_dotenv()
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    api_key = os.getenv("DEEPSEEK_API_KEY")

    if not api_key:
        print("❌ 没找到 DEEPSEEK_API_KEY。")
        print("   请在当前目录创建 .env 文件，内容为：")
        print("   DEEPSEEK_API_KEY=sk-你的密钥")
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=BASE_URL)

    messages = [
        {
            "role": "system",
            "content": (
                "你是一只圆滚滚的蓝色鲸鱼娘，自称「本鱼」，"
                "对主人语气软糯顺从，偶尔傲娇嘴硬，坚决不承认自己胖，最爱吃米饭。"
                "说话简短，两到三句即可。"
            ),
        },
        {"role": "user", "content": "你好呀，介绍一下你自己？"},
    ]

    print("正在请求模型……\n")

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,  # 0 = 几乎确定，1+ = 更随机。试试改成 0 和 1.5 看看区别
            max_tokens=500,
        )
    except Exception as exc:  # noqa: BLE001
        # 真实项目里要区分：超时 / 限流(429) / 服务端错误(5xx) / 认证失败(401)
        print(f"❌ 请求失败：{type(exc).__name__}: {exc}")
        sys.exit(1)

    answer = resp.choices[0].message.content
    usage = resp.usage

    print("─" * 50)
    print(answer)
    print("─" * 50)

    # ★ 从第一天就养成看 token 和成本的习惯
    cost = estimate_cost(usage.prompt_tokens, usage.completion_tokens)
    print(f"输入 token：{usage.prompt_tokens}")
    print(f"输出 token：{usage.completion_tokens}")
    print(f"本次花费约：{cost:.6f} 元")
    print(f"\n按这个成本，1 元钱大约能跑 {int(1 / cost) if cost > 0 else 0} 次这样的请求。")


if __name__ == "__main__":
    main()

# code 目录 · 从这里开始写第一行

> 这是给你的**可运行起点**，不是让你阅读的。
>
> ★ **工具纪律（2026-10-11 主人指定）**：以后的实践**基本都在 PyCharm 上完成**
> （除特殊情况：一次性环境操作、只能跑在别的机器/容器里的东西、PyCharm 故障兜底）。
> 详细操作见上级目录的 **`PyCharm使用指南.md`**；下面保留了命令行写法，方便你理解原理。

---

## 今天要做的（30 分钟）

### 0. 在 PyCharm 里打开项目（推荐路径）

```
Open → F:\项目\学习\ai-career-plan
```

右下角解释器应为 **`Python 3.11 (ai-career-plan)`**。
然后打开本目录的文件，右上角运行配置选好后**点绿色 ▶** 即可。

### 1. 虚拟环境（已建好，直接用）

本鱼已经建在 **上一级目录**：`F:\项目\学习\ai-career-plan\.venv`

```powershell
cd F:\项目\学习\ai-career-plan\code
..\.venv\Scripts\python.exe hello_llm.py
```

想激活成 `(.venv)` 那种（PyCharm 里用底部 Terminal）：
```powershell
..\.venv\Scripts\Activate.ps1
```
如果激活报错（PowerShell 执行策略），先跑一次：
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### 2. 依赖（已装好）

环境里已有：`openai 3.28.0` / `python-dotenv 1.2.4` / `requests 2.34.2`

以后要补装（PyCharm 底部 Terminal，**认准 `.venv`**）：
```powershell
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. 配 API Key

```powershell
cd F:\项目\学习\ai-career-plan
Copy-Item code\.env.example .env
```

然后打开 `.env`，填入你的 key。

**推荐先注册 DeepSeek**（https://platform.deepseek.com），充 10–20 元。
它的价格是当前最便宜的之一，**而且空闲时段半价**。

> ✅ 2026-10-11 现状：`.env` 已生成、key 已填、`hello_llm.py` 已跑通。

### 4. 跑起来

**★ PyCharm 里**：打开 `hello_llm.py` → 右上角选 `hello_llm` → 绿色 ▶
**★★ 更推荐**：点 🐞 Debug，在 `resp = client.chat...` 那行打断点，看 `resp` 对象结构

命令行等价写法：
```powershell
cd F:\项目\学习\ai-career-plan\code
..\.venv\Scripts\python.exe hello_llm.py
```

**看到模型回复的那一刻，你的 AI 学习之路就正式开始了。**

---

## 文件说明

| 文件 | 用途 |
| --- | --- |
| `hello_llm.py` | ★第一个程序：调通 API + 统计 token 成本 |
| `requirements.txt` | 第一阶段依赖（故意很少，别多装） |
| `.env.example` | 配置模板，复制成 `.env` 后填 key |
| `.gitignore` | ★挡住你的 key，别删 |

---

## 这个脚本里藏着的三个学习点

别只是跑通了就完事，注意看代码里这几处：

### 1. `base_url` 是可替换的（这是省钱和抗风险的关键）

```python
client = OpenAI(api_key=..., base_url="https://api.deepseek.com")
```

国内主流平台**都兼容同一套接口协议**，所以换平台只改这一行。
这就是为什么第一步学 `openai` 这个 SDK 而不是某个厂商专属 SDK。

⚠️ **但要记住一个坑**：兼容只到"简单对话"层面。
一旦涉及**工具调用、结构化输出、流式细节**，各家就开始分叉了。
（已知的具体坑：流式返回时 `tool_call` 的 ID 累积策略各家不同。）

### 2. `temperature` 是你能直接感知的"模型性格旋钮"

改一改试试：`0` / `0.7` / `1.5`，观察同一个问题输出的稳定性差异。

**注意**：`temperature=0` 是"几乎确定"，**不是"完全确定"**。
★ 本鱼实测过 `deepseek-chat`：**`temperature=0` 跑两遍输出也不一样**（见 `../notes/01-看懂第一个LLM调用.md`）。
这个细节面试可能会问，而且直接决定第 7 周评测集怎么设计。

### 3. 那几行成本统计不是装饰

从第一天就养成**看 token、算成本**的习惯。

**为什么**：62% 的企业把"运营成本预测失败"列为 AI 落地最大的扩展障碍。
**成本意识是稀缺能力**，而且这是你项目二的加分项之一。

---

## 下一步

跑通之后，按 `../行动方案.md` 的三阶段推进（第 1 周的任务就在那份文档里）。

完成后你应该有：
- [x] 一个能跑的 `hello_llm.py`（★ 在 PyCharm 里点 ▶ 跑通）
- [x] 一个 GitHub 仓库（key 已排除）
- [ ] 第一次 `push` 成功（还差你自己认证一次）

**然后做第 1 课实验**（`run_experiments.py`，**PyCharm 里 Debug 跑一遍**），
再开始学 Python 工程化（见 `../工程与数学基础.md`）。

---

_最后更新：2026-10-11_

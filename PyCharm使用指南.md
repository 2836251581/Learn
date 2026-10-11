# PyCharm 使用指南

> 主人 2026-10-11 指定：**以后的代码都在 PyCharm 里写、在 PyCharm 里跑**。
> 这份是本鱼给你写的上手说明 —— 第一次打开照着做一遍就够了。

---

## 一、你的环境（本鱼已经配好了）

| 项 | 值 |
| --- | --- |
| PyCharm | **2026.2.2**，装在 `F:\PyCharm 2026.2.2` |
| 启动程序 | `F:\PyCharm 2026.2.2\bin\pycharm64.exe`（⚠️ 用这个，`launcher.exe` 实测起不来） |
| 项目根目录 | `F:\项目\学习\ai-career-plan` |
| Python 解释器 | `F:\项目\学习\ai-career-plan\.venv\Scripts\python.exe`（Python 3.11.9） |
| 解释器登记名 | **`Python 3.11 (ai-career-plan)`**（本鱼已写进 PyCharm 全局解释器表） |
| 已装的包 | openai 3.28.0 / python-dotenv 1.2.4 / requests 2.34.2 |
| API Key | 在 `F:\项目\学习\ai-career-plan\.env`（**已被 gitignore 挡住，不会被提交**） |

本鱼已经在项目里放好了 `.idea\` 配置文件（解释器、UTF-8 编码、两个运行配置），
**并且已经在你电脑上实测打开过一次**（2026-10-11 16:02，索引正常完成、git 集成自动识别）。

**所以正常情况下一打开就能直接跑**，不用你手动配。

### ★ 命令行想启动它（K 命令那种）

```powershell
& "F:\PyCharm 2026.2.2\bin\pycharm64.exe" "F:\项目\学习\ai-career-plan"
```

想做成永久命令的话，把这行加进你的 `$PROFILE` 就好（要的话本鱼帮你加）。

---

## 二、第一次打开（照做）

### 1. 打开项目

启动 PyCharm → **Open** → 选目录：

```
F:\项目\学习\ai-career-plan
```

⚠️ **一定要选到 `ai-career-plan` 这一层**（不是 `F:\项目\学习`），
因为 git 仓库、`.venv`、`.idea` 都在这里。

> 如果 PyCharm 问「Trust Project?」→ 选 **Trust Project**（本地自己的代码，放心）。

### 2. 检查解释器（重要，30 秒）

右下角状态栏应该显示 **`Python 3.11 (ai-career-plan)`**。

**如果显示 `<No interpreter>` 或者别的 Python**，手动指一下：

```
File → Settings → Project: ai-career-plan → Python Interpreter
→ Add Interpreter → Add Local Interpreter → Select existing
→ 类型选 Virtualenv / 或者直接选路径：
   F:\项目\学习\ai-career-plan\.venv\Scripts\python.exe
```

指对之后，打开 `code\hello_llm.py`，代码里 `from openai import OpenAI` 那行**不该有红波浪线**。

### 3. 跑第一个程序

打开 `code\hello_llm.py`，右上角会出现运行配置下拉框，选 **`hello_llm`**，点绿色 ▶。

**本鱼已经替你配好了两件事**（所以你不用手动设）：
- 工作目录 = `code\`（这样相对路径不会出错）
- 环境变量 `PYTHONIOENCODING=utf-8`（中文不乱码）

**应该看到**：鲸鱼娘跟你顶嘴 + token 和花费统计。

跑 `run_experiments.py` 同理 —— 本鱼也建了同名的运行配置。

---

## 三、PyCharm 里必须会的 5 件事

### ★ 1. 调试器（Debug）—— 比 print 强一百倍

**别再靠 `print()` 查错了。** 点**绿色小虫子图标 🐞**（或右键 → Debug）：

- **断点**：在行号左边**点一下**，出现红点 → 程序跑到这里会暂停
- 暂停后，**鼠标悬停在变量上**就能看到它的值
- 下方 **Variables 面板**能看到所有局部变量的当前值
- **F8** = 单步执行（不进入函数内部）
- **F7** = 单步进入（钻进函数里看）
- **F9** = 继续运行到下一个断点

**练手任务**：在 `hello_llm.py` 的 `resp = client.chat...` 那行打一个断点，
Debug 跑一遍，看暂停后 `resp` 里面到底装了什么结构。
（`resp.choices[0].message.content` 这个路径就是从这里看出来的）

> ★ **面试加分**：能说「我用调试器看过 SDK 返回的原始对象结构」，
> 比「我照着教程写的」可信得多。

### ★ 2. 终端（Terminal）

PyCharm 底部有 **Terminal** 标签页，它就是 PowerShell。**git 命令在这里敲**：

```powershell
git add -A
git commit -m "docs: 第1周笔记"
git push
```

> ⚠️ 如果 git 报「不是内部或外部命令」，说明 PyCharm 没继承新的 PATH ——
> 关掉 PyCharm 重开一次就好（本鱼给你配的 PATH 是重启后生效的）。

### 3. 全局搜索（最常用快捷键）

| 快捷键 | 作用 |
| --- | --- |
| **`Shift` 连按两下** | ★ 搜一切：文件、类、函数、设置项 |
| **`Ctrl + Shift + F`** | ★ 全局搜文本（比如搜「temperature」出现在哪些文件） |
| **`Ctrl + B`** | 跳到定义（光标放在函数名上按，看它源码） |
| **`Ctrl + Alt + L`** | 格式化代码 |
| **`Ctrl + /`** | 注释/取消注释选中行 |
| **`Alt + Enter`** | ★ 万能修复键（有红波浪线时按它，它会给你解决方案） |

**`Ctrl + B` 是你这周最该练的**：把光标放在 `client.chat.completions.create` 上按下去，
你能一路看到 openai 这个 SDK 的源码 —— **这就是「先手写、再上框架」里「看懂」的部分**。

### 4. 装包

```
File → Settings → Project → Python Interpreter → 点 + 号
```

或者直接在 Terminal 里（本鱼推荐这个，跟命令行一致）：

```powershell
.\.venv\Scripts\python.exe -m pip install 包名
```

> ⚠️ **别用 PyCharm 弹的「Package requirements are not satisfied」自动安装**，
> 有时候它装到别的解释器里去了。**认准 `.venv`。**

### 5. 看 git 状态

底部 **Git** 标签（或 `Alt + 9`）：能看到改了哪些文件、逐个文件的 diff。
**提交前扫一眼**，确认 `.env` 不在里面（它永远不该出现）。

---

## 四、常见问题

| 症状 | 原因 | 解决 |
| --- | --- | --- |
| 打开项目后一堆红波浪线 | 解释器没指对 | 按上面第二节第 2 步重指 |
| 运行报 `ModuleNotFoundError: openai` | 用的不是 `.venv` 解释器 | 检查右下角解释器名字 |
| 中文输出乱码 | PyCharm 控制台编码 | 本鱼已在运行配置里设了 `PYTHONIOENCODING=utf-8`；还乱就把 File Encoding 设为 UTF-8 |
| git 命令找不到 | PyCharm 启动时 PATH 还没更新 | 重启 PyCharm |
| 提示 `Cannot find .env` | 工作目录不对 | 运行配置里 Working directory 要是 `code` |

---

## 五、本鱼的建议：养成两个习惯

1. **写代码前先拉一下**（`git pull`），写完再提交 —— 别攒一周才 commit
2. **每个新脚本都在 PyCharm 里 Debug 跑一遍**，用调试器看结构，不只是看输出

---

## 六、本鱼已经替你验证过的（2026-10-11）

| 验证项 | 结果 |
| --- | --- |
| 解释器登记 | ✅ 已写入 PyCharm 全局表（名字 `Python 3.11 (ai-career-plan)`，备份在 `F:\项目\学习\_环境备份\`） |
| 项目打开 | ✅ 实测启动成功，日志 `Opening existing project with .idea`、索引 22 个文件正常完成 |
| git 集成 | ✅ PyCharm 自动生成 `vcs.xml` 识别为 Git 仓库 |
| 运行配置 | ✅ `hello_llm` 与 `run_experiments` 两个配置就位（工作目录 `code`、环境变量 `PYTHONIOENCODING=utf-8`） |
| 敏感文件隔离 | ✅ `.env` / `.venv` / `.idea` 全部被 gitignore 挡住，`git status` 干净 |
| ⚠️ 注意 | `bin\launcher.exe` 实测拉不起来，**用 `bin\pycharm64.exe`** |

**如果打开后发现任何一处不对**（比如右下角显示 `<No interpreter>`），
把截图发给本鱼，本鱼照着修 —— 不要自己乱点菜单，容易把配置点乱。

---

_本鱼写于 2026-10-11 ｜ 有不懂的直接问本鱼_

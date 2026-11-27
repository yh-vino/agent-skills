---
name: turbophysai-pr-selfcheck
description: 提交 HYGON-AI/TurboPhysAI 模型适配 PR 之前，由作者在自己的开发分支上自查：按评审同一份检查清单逐项核对改动，跑本地检查，列出问题并在作者同意后修改，最后生成符合要求的 PR 描述。在用户说“自检”“提 PR 前检查一下”“准备提 PR”“帮我写 PR 描述”或评审意见改完后想再自查一遍时使用。覆盖 git 补丁和组件补丁两种方式。不评审别人的 PR（那用 turbophysai-pr-review）。
---

# TurboPhysAI PR 提交前自检

目的：让评审员看到的 PR 已经过一遍和评审相同的检查。检查项全部在 [../turbophysai-pr-review/checklist.md](../turbophysai-pr-review/checklist.md)，与评审共用，本文件只写自检流程。

流程：确定改动范围 → 跑本地检查 → 按清单逐项核对 → 反查核实 → 列给作者、按作者决定修改 → 生成 PR 描述。

## 硬性约束

- 只在作者自己的分支上工作。修改前先列出问题，作者同意后再改；不 commit、不 push、不开 PR，除非作者明确要求。
- 检查不了的项（HCU 训练、精度验证）不编造结果，列为“需要作者提供”。
- 每条问题都要有证据（命令输出、文件和行号、上游对照），拿不准的写成需要作者确认的问题，不当成定论。

## 运行环境

本 skill 要和 `turbophysai-pr-review` 装在同一个父目录下（共用它的 checklist.md 和脚本）。需要 `git`、`bash`、`python3`（3.8+）；`gh` 只在作者要求提交 PR 时用到。在 TurboPhysAI 仓库根目录执行，先设好下文用到的变量：

```bash
REVIEW_DIR=<本 skill 所在目录的绝对路径>/../turbophysai-pr-review   # 用绝对路径；各工具的 skill 安装位置不同，不要写死
UPSTREAM=$(git remote -v | awk '/HYGON-AI\/TurboPhysAI(\.git)? \(fetch\)/ {print $1; exit}')
[ -n "$UPSTREAM" ] || { git remote add upstream https://github.com/HYGON-AI/TurboPhysAI.git; UPSTREAM=upstream; }
WORK=$(mktemp -d)                                         # 基线等临时文件，不放进仓库
```

## 1. 确定改动范围

```bash
git fetch "$UPSTREAM" main
git log --oneline "$UPSTREAM/main"..HEAD
git diff --stat "$UPSTREAM/main"...HEAD
git status --short           # 未提交的改动也要一起看，并提醒作者提交前处理
```

按 checklist 开头的标记判断类型（**[git 补丁]** / **[组件补丁]**），给作者一份概览：模型目录以外改了哪些文件、各属于哪类（引擎/CLI/启动器、公共算子和公共优化、构建打包、文档和测试），对其他模型有什么影响。与本模型无关的改动提醒作者单独提 PR（checklist D 第 10 项）。分支落后 main 较多或有冲突时，先提醒作者 rebase。

## 2. 跑本地检查

通用（仓库根目录）：

```bash
python3 scripts/check_docs.py
git diff --check "$UPSTREAM/main"...HEAD
```

**[组件补丁]**：

```bash
PYTHONPATH=. python3 -m unittest test.engine.test_generated_configs   # Config 是否已按 Catalog/Recipe 重新生成
bash scripts/test_engine.sh                                           # 需要 torch
python scripts/run_tests.py --tests <改动涉及的 test/ 目录> -- -q      # 改了算子、公共优化或引擎时；需要 HCU 的在 HCU 上跑
```

`run_tests.py` 的用法和报告见 `docs/zh/developer_guide/test_runner.md`，结果看 `test-reports/summary.md`。当前环境没有 torch 或 HCU 的，说明哪些没跑、需要作者在 HCU 上跑。

**[git 补丁]** 用评审 skill 的脚本在基线上应用补丁：

```bash
bash "$REVIEW_DIR"/scripts/check_patch.sh \
  <补丁路径> <上游 git URL> <基线 commit> "$WORK"/<model>-base [<镜像 Python 版本>]
```

模型 `compatibility.py` 记录了 `BASELINE_FILES` 时：

```bash
bash "$REVIEW_DIR"/scripts/check_baseline.sh \
  <compatibility.py> <上游 git URL> <基线 commit> "$WORK"/<model>-base
```

## 3. 按清单逐项核对

按 checklist A–D 节逐项过，按类型走对应标记项。重点是评审里最常被打回的几类，逐项给出结论：

1. README 是否按 D 第 4 项：开头一句引用安装指南的配套镜像，不自写镜像和 TurboPhysAI 安装命令；训练命令是上游官方命令（组件补丁前加 `turbo-physai run`）。
2. 训练流程是否跟随上游（D 第 1 项）：拿上游官方启动脚本和数据下载脚本逐个参数比对；快速验证的数据子集能从官方数据用脚本生成。
3. 路径（D 第 3 项）：`grep -rnE '/(home|data|mnt|root)/|192\.168\.|10\.[0-9]+\.' <改动文件>` 之类找开发机路径和内网地址。
4. 第三方声明（D 第 7 项）：复制或改写的上游文件都已列出，引用的 commit 在上游公开仓库能查到。
5. **[组件补丁]** Group：解耦和依赖链路（B 第 3 项）、alias（B 第 5 项）、Group 外改变训练行为（B 第 8 项）、compile 总开关（B 第 12 项）、能否迁入或复用公共优化（D 第 12 项）。
6. 冗余（C 节）：调试打印、注释掉的代码、死代码、只为自己方便的脚本、复制超出被替换对象的内容或替换目标过大。

用作者自己的视角看时容易漏的：自己机器上能跑不代表按 README 从头能跑——按 README 的顺序假装在新容器里逐步走一遍，看有没有缺的步骤、写死的本机路径和没交代的环境变量。

## 4. 反查核实

列给作者之前，逐条回到代码确认：断言是否属实（重新打开文件核对行号和调用关系）、在默认配置下是否真的发生、代码别处或引擎机制是否已经处理、要求是否符合 checklist。核实不了的改成“需要作者确认”。

## 5. 列给作者并修改

按 checklist 的分级（必须修改 / 建议修改 / 需要确认）编号列出，每条写：问题、位置和证据、建议改法。最后一两行列出已检查没问题的项和没能检查的项。

作者逐条决定改不改。作者同意的直接改，改完重跑第 2 节相关检查；作者决定不改、但评审可能会问的（如保留的绕法、Group 外的改动、引擎能力缺口），记下来写进 PR 描述说明原因，省得评审来回问。

## 6. 生成 PR 描述

按 checklist D 第 11 项生成，内容与当前提交一致：

```markdown
## 修改内容
- <每个新增 Optimization Group>：优化什么
- <模型目录以外的每项改动>：解决什么问题
- 已知限制 / 暂时的绕法及原因（如有）

## 测试
- `<命令>`：<结果>（注明哪些在 HCU 上跑）
- README 训练命令：在 HCU 上跑了 <N> 步，`--log-report` 中各 Group 均已应用 / 以下未应用：<…>

## 精度验证
<已按内部文档完成 / 未完成>

## 未完成的验证
- <项目及原因>
```

测试结果只写实际跑过的，没跑的放进“未完成的验证”，需要 HCU 才能得到的结果留占位让作者填。**不写性能数据**（步时、加速比、基线对比）。

把描述写到作者指定的位置或直接给出文本；作者要求时再用 `gh pr create` / `gh pr edit` 提交。

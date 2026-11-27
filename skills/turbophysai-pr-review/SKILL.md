---
name: turbophysai-pr-review
description: 评审 HYGON-AI/TurboPhysAI 的模型适配 PR，覆盖两种方式：git 补丁（model_examples/<Model>/*.patch）和组件猴子补丁（turbo_physai/optimizations/ 下的 Catalog、Replacement 和配置）。在用户说“评审/审阅 PR #N”“看看这个 PR”“PR 有更新/有回复再看一下”或给出 TurboPhysAI 的 PR 链接时使用。产出逐条可确认的评审草稿，并在用户确认后创建待提交（pending）的 GitHub review，不代为提交。作者提交前的自查用 turbophysai-pr-selfcheck。
---

# TurboPhysAI PR 评审

流程：读已定口径 → 同步 → 判断类型 → 验证 → 按清单审查 → 起草 → 逐条反查核实 → 用户逐条确认 → 建 pending review。检查项全部在 [checklist.md](checklist.md)（与自检 skill 共用），本文件只写评审流程。每条结论都要有证据（命令输出、行号、上游对照），不确定的写成询问。

## 硬性约束

- **不代为提交 review、不 push**。只创建 pending review，由用户在 GitHub 上提交；发布前用户必须确认最终文本。回复已有线程、标记 resolve 只在用户明确要求时做（见第 8 节）。
- 不动用户当前仓库的工作区：PR 代码放独立 worktree，上游基线和临时文件放 `$WORK`。
- 结论要在 PR 目标环境下验证（镜像里的 Python 版本、requirements 钉住的依赖版本），不能拿本机版本的行为下结论。

## 运行环境

需要 `git`、`bash`、`python3`（3.8+）和已登录的 `gh`（`gh auth status` 确认）；脚本只用 Python 标准库。在 TurboPhysAI 仓库根目录执行，先设好下文用到的变量：

```bash
SKILL_DIR=<本 skill 所在目录的绝对路径>  # 用绝对路径（后面会 cd 到 worktree）；各工具的 skill 安装位置不同，不要写死
UPSTREAM=$(git remote -v | awk '/HYGON-AI\/TurboPhysAI(\.git)? \(fetch\)/ {print $1; exit}')
[ -n "$UPSTREAM" ] || { git remote add upstream https://github.com/HYGON-AI/TurboPhysAI.git; UPSTREAM=upstream; }
WORK=$(mktemp -d)                      # 基线、review JSON 等临时文件，不放进仓库
```

## 0. 已定口径

开始前确认这个 PR 或这类问题有没有已定口径（团队决定不合入的部分、暂时接受的绕法、维护者计划自己统一的重复实现等），按口径评审，不重复提已经定过的事。所用工具有持久记忆的查记忆；没有的，开始前问用户。

用户在评审中拍板一项决定（某部分保留/移除、某问题后续再做、某规则以后都这样）时：只关乎这个 PR 的，有持久记忆就记下（写明 PR 号、日期、原因、何时失效），没有就在评审结束时提醒用户自己留存；对以后所有 PR 都适用的，问用户是否写进 checklist.md。

## 1. 同步 PR

```bash
PR=<编号>
git fetch "$UPSTREAM" main "pull/$PR/head"
HEAD_SHA=$(git rev-parse FETCH_HEAD)   # FETCH_HEAD 按 worktree 区分，必须在执行 fetch 的仓库里取
WT=../TurboPhysAI-pr$PR
[ -d "$WT" ] || git worktree add --detach "$WT" "$HEAD_SHA"
git -C "$WT" reset --hard "$HEAD_SHA"
gh pr view $PR -R HYGON-AI/TurboPhysAI --json title,body,author,headRefOid,commits,files,mergeable
python3 "$SKILL_DIR"/scripts/pr_threads.py $PR
```

`pr_threads.py` 列出全部评审线程（解决状态、是否 outdated、最后一条回复）、合并冲突状态，以及用户是否还有未提交的 pending review（用户问“评论发了吗”时也用它查）。`mergeable` 为 `CONFLICTING` 时告诉用户冲突的文件。

**首次评审**也要核实已有评论（AI 机器人和其他评审人），逐条按当前代码和钉住版本核实：成立的并入草稿，不重复提；不成立或已修复的告诉用户原因。

**复审**时先告诉用户作者做了什么：
- 列出上次评审后的新提交（`git log <上次SHA>..$HEAD_SHA`），概括每个提交改了什么。
- 按 `pr_threads.py` 的结果逐条对照新代码，列表标出：已修改 / 只回复未修改 / 标记解决但没回复也没改 / 未处理。作者在别的线程里的解释不算处理了这一条。作者的改法也要看：是否按评论的意思改对了。
- 上游 main 有更新时（尤其是安装指南、已合入模型的 README、引擎能力），按 main 的新状态重新核对相关检查项。

## 2. 判断 PR 类型和改动范围

- **[git 补丁]**：改动包含 `model_examples/<Model>/*.patch`，补丁打到上游模型仓库上。
- **[组件补丁]**：改动包含 `turbo_physai/optimizations/`（`catalog.py`、Replacement 实现、`configs/`）或 `turbo_physai/operators/`，运行时通过 `turbo-physai run` / `turbo_physai.apply()` 替换模型对象，不改模型源码。
- 都不是的（框架、构建、纯文档）只做通用评审，并告诉用户本 skill 尚未覆盖。

评审范围以实际改动为准，不受 PR 描述限制（描述没提的推理适配等也要评）。

先给用户一份**改动范围概览**：
- 模型目录（`optimizations/models/<model>/`、`model_examples/<Model>/`）以外改了哪些文件，按“引擎/CLI/启动器（`turbo_physai/engine/`、`cli.py`、`runtime.py`、`runner.py`）”“公共算子和公共优化”“构建打包”“文档和测试”分类，并说明对其他模型的影响和生效条件。
- 改动量大（几千行以上）时，按类别给出行数构成：实质新逻辑、从上游/第三方复制的代码、生成文件、测试、文档，让用户知道代码量花在哪里。复制的代码按 checklist C 第 3 项判断：被替换对象的完整复制属于正常，只看有没有复制超出范围或替换目标过大。

## 3. 验证

通用：作者提供的下载命令、数据处理脚本、数据包等，要实际验证后再下结论，但控制在小范围：下载只验证命令能解析、能拉到一两个文件，处理脚本用小样本跑。需要下载大数据集或权重、或预计超过 10 分钟的验证，先问用户。

**[git 补丁]** 从 README 读出上游仓库地址、基线 commit 和镜像里的 Python 版本：

```bash
bash "$SKILL_DIR"/scripts/check_patch.sh \
  <补丁路径> <上游 git URL> <基线 commit> "$WORK"/<model>-base [<Python 版本，如 3.10>]
```

脚本会浅拉取基线（跳过 LFS 内容，约 20 秒）→ 应用补丁 → 反向应用检查 → 按目标 Python 版本检查改动的 `.py` 语法 → 输出新增/修改/删除文件清单（供第三方声明比对）。

**[组件补丁]** 在 PR worktree 里运行本机不依赖 HCU 和模型环境的检查：

```bash
cd "$WT"
PYTHONPATH=. python3 -m unittest test.engine.test_generated_configs
python3 scripts/check_docs.py
git diff --check "$UPSTREAM/main"...
```

第一项检查所有 `optimization.yaml` 与 Catalog、Recipe 是否和生成记录一致，改了配套文件却没重新生成 Config 时会报错。engine 测试和 HCU 测试依赖 torch 与 HCU 环境，本机跑不了，只检查 PR 描述是否列出已执行的测试命令和结果。

模型的 `compatibility.py` 记录了基线文件哈希（`BASELINE_FILES`）时，核对它与上游基线一致，并看上游 main 是否已改动这些文件：

```bash
bash "$SKILL_DIR"/scripts/check_baseline.sh \
  <compatibility.py> <上游 git URL> <基线 commit> "$WORK"/<model>-base
```

脚本只浅拉基线；上游 main 通过 GitHub API 逐文件比对，不拉取 main（main 的目录树可能远大于基线，fetch 会卡住）。基线目录可直接用于第 4 节的代码对照。

查某个 commit 是否存在于上游，用 `gh api repos/<owner>/<repo>/commits/<sha>`（返回 422 即不存在），不要用 `git fetch`：fetch 不存在的 SHA 可能长时间挂起。

## 4. 按清单审查

按 [checklist.md](checklist.md) 的 A–D 节逐项过，按 PR 类型走对应的标记项。读有实质逻辑的部分；纯配置、文档、测试数据扫一眼即可。需要和上游最新代码对比时（是否已被上游修掉或重构；大段删除或移动先确认是不是挪到了别处），在基线目录里 `git fetch --depth 1 <上游 URL> main` 后只 diff 相关文件。

对照时以上游 main 的当前状态为准（安装指南、已合入模型的写法、`docs/zh/` 里的约定），不凭记忆。

## 5. 起草

按“必须修改 / 建议修改 / 询问”分组并编号（讨论过程中编号保持不变）。每条给用户：
- 一句大白话背景（这是什么、为什么重要），供用户判断；涉及环境变量、运行时机制或上游约定时（如 `ROCR_VISIBLE_DEVICES`、DeepSpeed 梯度累积），顺带解释它是什么、通常由谁设置、用户是否需要操作，不假设用户已经知道；
- 位置和证据；
- 评论草稿。

最后用一两行列出已检查且没问题的项。

评论草稿的要求：
- 只提有实际影响的问题；不是核心功能的小提醒（用户照着 README 做就不会出错的）不提。
- 不索要、不提及性能数据（步时、加速比、基线对比）；PR 里已有的由用户私下处理。
- 第 0 节已定口径里定过的不提；维护者计划自己统一处理的问题不提，免得干扰作者。
- 用用户的口吻：中文、简短直接、不寒暄；先说问题再说怎么改；一条只讲一件事，挂在具体代码行上。
- 写清触发条件、涉及的每处代码各做了什么、后果、改法。跨文件时分开写，不混淆不同函数的返回值；补丁内的位置同时给补丁行号和原始文件路径。
- 改法涉及函数约定（返回值、参数）时，追到所有调用方，把需要同步改的位置都写上。
- 取证过程（如“已核对上游某提交”）只告诉用户，不写进评论。
- 拿不准是否必要的改动，写成：“确认是否必要，不必要就删掉；必要的话……（说明风险）”。
- 发出前站在作者角度通读一遍，确认不看上下文也能看懂。

**总评**：一两句点出最需要确认的风险，一句概括其余建议，说明具体见行内评论。不重复行内内容。

**复审结论**分开说：修复方向是否认可；本地做了哪些检查并通过。CI 在合入后才触发，评审时不看 CI 状态。

## 6. 逐条反查核实（给用户之前）

草稿全部写完后，**逐条回到代码反查一遍**，确认每条评论符合事实、要求合理，再交给用户。不能把“等用户追问再细查”当作流程的一部分。每条都过以下几项：

1. **事实**：评论里的每个断言（文件和行号、调用关系、执行时机、版本差异）都重新打开代码或钉住版本的源码核对；能用几行代码复现的（如导入绑定、子进程行为）就实际跑一下。
2. **触发条件**：问题在交付配置和默认参数下是否真的发生；只在非默认配置下发生的，降级或写明条件。
3. **找反证**：主动找“其实已经处理了”的证据——代码别处的兜底、引擎已有机制（alias、`--disable-group`、生成检查）、仓库已有约定（`docs/zh/` 里搜相关关键词）、已合入模型对同类问题的写法（同类写法在已合入模型里没出问题的，先弄清差别再提）。
4. **合理性**：要求是否符合 checklist 和第 0 节的已定口径；改法是否最简单、和现有代码写法一致；分级是否恰当。
5. **措辞**：评论只写核实过的内容；核实不了的改成询问或删掉；按第 5 节通读一遍。

核实后给用户的清单里，每条标明结论：**成立**、**已修正**（说明改了什么）、**撤回**（说明原因）。撤回的不进草稿，但要列出来让用户知道。

用户逐条决定提/不提/改措辞。用户纠正事实时先复核，明确说出之前哪里错了。

## 7. 创建 pending review

1. 重新取 PR head；与起草时不同就检查锚点行是否还对应原内容，有变化回到第 5 步。
2. 把定稿写成 JSON（放 `$WORK`），`line` 为 PR head 版本中该文件的行号：

   ```json
   {"repo": "HYGON-AI/TurboPhysAI", "pr": 19, "head": "<sha>", "body": "总评",
    "comments": [{"path": "setup.py", "line": 14, "body": "..."}]}
   ```

3. 先 `--dry-run` 校验（不创建任何东西），通过后再正式创建。不要拿真实 PR 试跑正式命令。

   ```bash
   python3 "$SKILL_DIR"/scripts/post_pending_review.py <review.json> --dry-run
   python3 "$SKILL_DIR"/scripts/post_pending_review.py <review.json>
   ```

   脚本会校验 head SHA、检查用户是否已有 pending review（每人每个 PR 只能有一个）、检查每个 `line` 是否落在该文件的 diff hunk 内（hunk 外的行 GitHub 会拒绝，需换到附近的改动行），创建后回读打印。

4. 提醒用户：到 Files changed → Finish your review 提交；有必须修改项时一般选 **Request changes**，用户也可以选 Comment（如想等作者改好后再统一处理），由用户定；GitHub 提交框不显示 API 预设的总评，提交前要把总评粘贴进去（附上原文）。

## 8. 评审后的线程操作

只在用户明确要求时做，做之前把要操作的线程列给用户确认：

- **在已有线程下回复**（如对某条补充说明）：回复挂在对应线程上，不另开评论。

  ```bash
  gh api graphql -f query='mutation($t: ID!, $b: String!) { addPullRequestReviewThreadReply(input: {pullRequestReviewThreadId: $t, body: $b}) { comment { url } } }' -f t=<thread id> -f b='<回复>'
  ```

- **标记 resolve**：只 resolve 用 `pr_threads.py` 和新代码核实为“已修改”的线程；只回复未修改的留给用户决定。

  ```bash
  gh api graphql -f query='mutation($t: ID!) { resolveReviewThread(input: {threadId: $t}) { thread { isResolved } } }' -f t=<thread id>
  ```

thread id 取自 `pr_threads.py` 的输出。操作后再跑一次 `pr_threads.py` 回读结果。

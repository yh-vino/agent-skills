---
name: turbophysai-adapt
description: 在 HCU 上端到端适配和优化一个新模型并接入 TurboPhysAI：立项定目标 → 环境与模型梳理 → 跑通适配 → Baseline 与 Profiling → 瓶颈驱动的优化循环 → 优化后验证 → 组件交付 → 经验沉淀。全程按组内《HCU适配与性能优化报告模板》和《接入交付报告模板》填写产物，并维护可续做的状态文件。在用户说“适配一个新模型”“开始做 <模型> 的 HCU 适配/优化”“继续 <模型> 的适配”“填优化报告/交付报告”“这个瓶颈怎么优化并接入”时使用。不评审别人的 PR（用 turbophysai-pr-review），提 PR 前的自检用 turbophysai-pr-selfcheck。
---

# TurboPhysAI 模型适配与优化

把一个新模型从“能在 HCU 上跑”推进到“优化后交付进 TurboPhysAI”。本 skill 管流程、门禁、产物和落地规范；每个阶段的做法在 `stages/` 里，按当前阶段只读对应文件。

```
00 立项 → 01 环境与模型 → 02 HCU 适配 → 03 Baseline 与 Profiling
      → 04 瓶颈与优化（循环） → 05 优化后验证 → 06 交付 → 07 沉淀
```

| 阶段 | 文件 | 对应《优化报告》章节 | 门禁（通过才进入下一阶段） |
|---|---|---|---|
| 00 立项 | [stages/00-kickoff.md](stages/00-kickoff.md) | 文档信息、1 概述 | 目标可量化；精度判定标准已确认 |
| 01 环境与模型 | [stages/01-environment.md](stages/01-environment.md) | 2 模型与测试环境 | 测试方法、sample 定义、计时口径已写清 |
| 02 HCU 适配 | [stages/02-adaptation.md](stages/02-adaptation.md) | 3 HCU 适配 | 3.7 适配结果各项通过 |
| 03 Baseline 与 Profiling | [stages/03-baseline.md](stages/03-baseline.md) | 4 Baseline 与竞品对比 | Baseline 精度正确；4.4 耗时拆解齐全 |
| 04 瓶颈与优化 | [stages/04-optimize.md](stages/04-optimize.md) | 5 性能瓶颈分析与优化 | 达到性能目标，或剩余瓶颈都有不处理的理由 |
| 05 优化后验证 | [stages/05-validation.md](stages/05-validation.md) | 6 优化后验证 | 精度、性能、稳定性达标 |
| 06 交付 | [stages/06-delivery.md](stages/06-delivery.md) | 《接入交付报告》全部 | 自检通过，PR 已提交 |
| 07 沉淀 | [stages/07-retrospect.md](stages/07-retrospect.md) | 7 总结与沉淀 | 每个 OPT 都有复用结论 |

改代码（阶段 02、04）时必须按 [landing.md](landing.md) 落地；选优化手法时查 [patterns/index.md](patterns/index.md)。

## 硬性约束

- **HCU 和竞品上的运行由人执行。** AI 写命令、读日志和 trace、改代码、填报告；需要实际运行的步骤给出完整命令，等用户把结果放进工作区再继续。拿不到的数据标“待提供”，**不编造任何数字**，也不从其他模型的报告里借数字。
- **门禁不跳。** 门禁未通过时不进入下一阶段；用户明确决定跳过时，在 `state.json` 记为 `waived` 并写明原因和决定人。
- **数字只进优化报告。** 性能数据（步时、吞吐、加速比、显存对比）只写在工作区的优化报告里，不进代码、commit、README、PR 描述和交付报告（交付报告只引用优化报告链接）。
- **跟随上游官方流程。** 不改训练 recipe（数据、权重、超参、冻结策略）；HCU 必需的调整单独列出并说明原因。
- **改代码前先给方案。** 每个 OPT 先列出目标、手法、落地位置和验证方式，用户同意后再改；不 commit、不 push、不开 PR，除非用户明确要求。
- **一次推进一两个瓶颈。** 按排行从高到低做，每个 OPT 合入后先做快速精度检查再叠加下一个。

## 工作区

每个模型一个工作区，**放在 TurboPhysAI 和模型仓库之外**（报告含性能数据，不能误提交）。首次使用时创建：

```bash
SKILL_DIR=<本 skill 所在目录的绝对路径>
python3 "$SKILL_DIR"/scripts/workspace.py init --model <ModelName> \
    [--workspace ~/turbophysai-adapt/<ModelName>] \
    [--upstream <上游 git URL>] [--commit <接入基线 commit>] [--category <自动驾驶|VLA具身智能|世界模型|视觉训练推理|其他>]
```

生成的目录：

```
<workspace>/
  state.json                 阶段、门禁、BOT/OPT/ISSUE 编号与状态、产物路径（只放索引，不放性能数字）
  reports/optimization-report.md   《HCU适配与性能优化报告》草稿
  reports/delivery-report.md       《接入交付报告》草稿
  traces/  logs/  env/  notes/     用户放入的原始数据和 AI 的中间记录
```

续做时先运行 `python3 "$SKILL_DIR"/scripts/workspace.py status <workspace>`，读出当前阶段、未通过的门禁和进行中的 OPT，再读对应的 `stages/` 文件。每完成一步就更新 `state.json` 和报告对应章节；两者不一致时以报告为准，并修正 `state.json`。

`state.json` 字段（`workspace.py init` 写出初始值）：

| 字段 | 内容 |
|---|---|
| `model` | 名称、类别、任务、上游仓库、接入基线 commit、模型仓库本地路径 |
| `stage` | 当前阶段 ID，如 `04-optimize` |
| `gates.<阶段>` | `status`（`open` / `passed` / `waived`）、`evidence`（工作区内文件路径或报告章节）、`note` |
| `bottlenecks[]` | `id`（BOT-xx）、`summary`、`category`、`evidence`、`opts`（关联 OPT 编号）、`status`（`open` / `addressed` / `deferred`） |
| `optimizations[]` | `id`（OPT-xx）、`name`、`bots`、`category`、`groups`（交付的 Group ID）、`location`（`common` / `models/<model>` / `git-patch`）、`status`（`proposed` / `implementing` / `validated` / `delivered` / `rejected`）、`accuracy`（`unchanged` / `verified` / `accuracy_only`）、`reuse`（阶段 07 填） |
| `issues[]` | `id`（ISSUE-xx）、`summary`、`status`、`vendor_fix`（是否需厂商修复） |
| `decisions[]` | 日期、内容、决定人（目标变更、门禁豁免、方案取舍） |

编号全局递增，不因分类重排；放弃的 OPT 保留编号，状态记为 `rejected`，写进报告“未采纳的优化尝试”。

## 报告输出

两份报告按模板结构写成 markdown，章节编号与飞书模板一致（2.4.2、4.4.1、5.1 等引用可直接对上）。用户要求同步到飞书且环境有 lark-cli 时，再用 lark-doc skill 写入用户指定的文档；默认只写本地文件。

## 相关文档（按需读取）

- `docs/zh/developer_guide/optimization_workflow.md`：基线 → 声明 → 生成配置 → 验证 → 评审的主线
- `docs/zh/developer_guide/optimization_declarations.md`：`group` / `replace` / `wrap` / alias / `runtime_condition` / `compatibility_check` / `options`
- `docs/zh/developer_guide/optimization_config_generation.md`、`docs/zh/reference/cli.md`：配置生成与 `turbo-physai run` 参数
- `docs/zh/developer_guide/validation.md`：各类改动的验证要求
- `../turbophysai-pr-review/checklist.md`：评审清单；落地规范与它保持一致，冲突时以清单为准并更新 landing.md

# agent-skills

个人沉淀的 Agent Skill，同时适用于 Claude Code 和 Codex。

| Skill | 用途 |
|---|---|
| `turbophysai-pr-review` | 评审 TurboPhysAI 模型适配 PR，生成逐条评审草稿，确认后创建 pending review |
| `turbophysai-pr-selfcheck` | 提 PR 前作者自查，与评审共用同一份检查清单，并生成 PR 描述 |
| `turbophysai-adapt` | 在 HCU 上端到端适配、优化新模型并接入 TurboPhysAI（8 个阶段，附报告模板） |
| `integrate-dasdriving-optimization` | 把已有模型或算子优化接入 dasDriving / TurboPhysAI，生成并校验 ModelPlan |
| `write-professional-docs` | 编写和审阅 README、安装指南、接入指南等技术文档 |

> `turbophysai-pr-selfcheck` 和 `turbophysai-adapt` 会引用 `turbophysai-pr-review/checklist.md`，请把三者装在同一目录下。
> `turbophysai-pr-review` 需要已登录的 `gh` CLI。

## 获取

```bash
git clone https://github.com/yh-vino/agent-skills.git ~/agent-skills
```

## Claude Code

把需要的 skill 链接到 Claude Code 的 skill 目录：

```bash
# 全局可用
mkdir -p ~/.claude/skills
ln -s ~/agent-skills/skills/* ~/.claude/skills/

# 或只在某个项目中可用（在项目根目录执行）
mkdir -p .claude/skills
ln -s ~/agent-skills/skills/* .claude/skills/
```

重启 Claude Code 后即可使用：直接用自然语言描述任务（如“评审 PR #40”），或输入 `/turbophysai-pr-review` 显式调用。

## Codex

```bash
mkdir -p ~/.codex/skills
ln -s ~/agent-skills/skills/* ~/.codex/skills/
```

重启 Codex 或新建任务后即可使用：直接描述任务，或在提示中写 `$turbophysai-pr-review` 显式调用。

## 更新

```bash
cd ~/agent-skills && git pull
```

使用软链接安装时，拉取后无需重新安装。

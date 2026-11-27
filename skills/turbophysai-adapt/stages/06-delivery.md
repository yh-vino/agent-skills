# 06 交付

目的：把验证过的配置作为组件交付进 TurboPhysAI，并填写《接入交付报告》。

产出：代码 PR；《接入交付报告》（第 1 章基本信息、第 2 章 Group 与 OPT 对应关系、第 3 章公共算子单测）。

## 步骤

1. **补齐仓库文件**（要求见评审清单 D 节）：
   - `model_examples/<Model>/README.md`：以 BEVFormer、BEVFusion、OpenVLA 的 README 为参照；开头一句引用安装指南的配套镜像；训练命令是上游官方命令前加 `turbo-physai run`；说明怎么确认优化已生效（`--log-report`）、怎么用 `--optimization-config` / `--runtime-config` 自定义。
   - `model_examples/<Model>/requirements.txt`：只在镜像缺依赖或版本与上游不一致时提供（清单 D 第 5 项）。
   - `docs/zh/models/support_list.md`：新增条目，基线 commit 与 README 一致。
   - `THIRD_PARTY_NOTICES.md`：复制或改写的上游、第三方代码都列出。
2. **重新生成并检查配置**：

   ```bash
   turbo-physai optimization generate --recipe <recipe.yaml> --repo <模型仓库> \
       --commit <接入基线 commit> --output <configs/optimization.yaml> --force
   turbo-physai optimization check --generated-only <configs/optimization.yaml>
   PYTHONPATH=. python3 -m unittest test.engine.test_generated_configs
   ```

3. **单测与覆盖率**：改了 `turbo_physai/operators/`、`turbo_physai/optimizations/common/` 或引擎时：

   ```bash
   python scripts/run_tests.py --tests <涉及的 test/ 目录> -- -q
   ```

   报告在 `test-reports/summary.md`，需要 HCU 的测例在 HCU 上跑。未覆盖的文件和场景写进交付报告第 3 章的说明表；没有涉及公共算子时第 3 章填“不适用”。模型专用优化不要求单测，由优化报告的端到端精度证据保证。
4. **生成交付报告第 2 章**：

   ```bash
   python3 "$SKILL_DIR"/scripts/workspace.py delivery-table <workspace>
   ```

   脚本根据 `state.json` 列出每个交付 Group 与 OPT 的对应关系；“生效证据”列填 `--log-report` 日志在工作区的位置或优化报告对应章节。一个 Group 对应多个 OPT、一个 OPT 由多个 Group 组成都可以；Group 里有多个替换时注明具体是哪个 replace。
5. **自检**：调用 `turbophysai-pr-selfcheck`，按评审清单逐项核对并生成 PR 描述。PR 描述**不写性能和精度数据，也不引用优化报告链接**，只说明修改内容、已执行的验证及结果、是否做过精度验证、未完成的验证。
6. **提交**：用户明确要求后再提 PR。提交后检查 Quality Gate 和 HCU CI；Fork PR 会跳过 HCU CI，需要维护者把待测提交放到主仓库可信分支后手动触发。
7. 填《接入交付报告》第 1 章：模型名称及版本、负责人、PR 链接、优化报告链接、组件 commit 或版本、模型配置链接、使用说明链接。

## 门禁

- [ ] 自检无“必须修改”项。
- [ ] 配置检查和 `test_generated_configs` 通过；涉及公共件时单测在 HCU 上通过。
- [ ] 交付报告第 1～3 章填完。
- [ ] PR 已提交，CI 结果已确认（或已请维护者触发 HCU CI）。

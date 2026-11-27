# 02 HCU 适配

目的：让模型在 HCU 上“跑起来且结果正确”。这一阶段只做必需的改动，不做性能优化（性能优化都放到阶段 04，才能算清每一项的收益）。

产出：《优化报告》第 3 章（3.1 框架侧、3.2 算子侧、3.3 三方库与自定义扩展、3.4 通信、3.5 数据类型与精度、3.6 适配问题与解决方案、3.7 适配结果）；`state.json` 的 `issues[]`；一份“跑通所需”的 recipe。

## 步骤

1. **按上游官方流程准备环境**：使用安装指南里对应类别的配套镜像（自动驾驶 / VLA、DiT 和世界模型），克隆上游并检出基线 commit，按 `notes/upstream.md` 的官方步骤安装依赖。镜像缺依赖或版本冲突的，记下来，阶段 06 用于决定是否需要 `model_examples/<Model>/requirements.txt`。
2. **先看公共件能自动覆盖什么**：不指定模型配置时，`turbo-physai run` 加载默认公共配置 `common.hcu.base`。让用户跑一次短训练并打开报告：

   ```bash
   cd <模型仓库>
   turbo-physai run --log-report <上游官方训练命令>
   ```

   从 OptimizationReport 里读出每个公共 Group 的状态：
   - `applied`：公共件已生效。属于“跑通必需”的（如替换 HCU 上不可用的算子）记进 3.2 / 3.3；属于性能优化的，留到阶段 04 作为第一个 OPT。
   - `blocked` 且原因是目标无法解析（模型不用 mmcv 等，目标库不存在）：正常，不用处理。
   - `blocked` 且原因是源码哈希不匹配（`source.identity`）：说明该库版本和公共件验证过的版本不同。记一条 ISSUE，不用 `--force-group` 绕过，交给维护者判断能否扩展兼容范围。
3. **逐个处理跑不通的问题**：每个问题一条 ISSUE（现象、根因、解决方案、是否需要厂商修复、状态）。处理顺序：
   1. TurboPhysAI 已有的公共算子或公共 Group → 直接用；
   2. 厂商版本（DTK 版 torch、厂商提供的三方库）→ 记版本；
   3. 需要新写的兼容处理 → 按 [landing.md](../landing.md) 落地：导入阶段的问题用导入兼容 Group（`replace_import` / `import_alias` / `optional_import` / `registry_override`），对象级问题用 `replace` / `wrap`；需要编译的 kernel 按 `docs/zh/developer_guide/custom_operator.md` 放 `kernel/<op>/`；
   4. 回退 CPU 或低效实现的算子，在 3.2 标注，它们通常就是阶段 03 的瓶颈。
4. **通信与精度格式**（3.4、3.5）：分布式策略、通信库和关键环境变量；FP32 / TF32 / BF16 / FP16 支持情况和与竞品默认行为的差异（例如竞品默认开 TF32 matmul）。
5. **写“跑通所需”recipe**：只包含本阶段必需的 Group，用它生成配置并作为阶段 03 的 Baseline 配置。没有任何必需 Group 时，Baseline 就是不经过 TurboPhysAI 的原生运行。

## 门禁（3.7 适配结果）

- [ ] 单卡跑通；单机多卡跑通；多机跑通（如在范围内）。
- [ ] Checkpoint 保存和加载正常。
- [ ] 短时 loss 曲线与竞品初步对齐（按 2.4.2 的训练过程层级）。
- [ ] 所有 ISSUE 都有状态；需厂商修复的已提给厂商。

## 常见问题

- 模型在模块导入时就出错（导入时现场编译扩展、目标在 `__main__` 启动脚本里），普通 Group 来不及拦截：这是引擎能力缺口（评审清单 B 第 9 项），先用最小绕法跑通，在 ISSUE 和代码 TODO 里写明，引擎改动单独提。
- 想顺手做性能优化：先记成 BOT 候选放进 `notes/`，阶段 04 再做。

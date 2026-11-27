# 01 环境与模型

目的：把测什么、在哪测、怎么算写清楚，保证 HCU 和竞品的数字可比、别人能复现。

产出：《优化报告》第 2 章（2.1 模型架构、2.2 数据集与数据处理、2.3 测试环境、2.4 测试方法与指标说明），附录 B、C。

## 步骤

1. **模型架构（2.1）**：读模型源码，给出模块级汇总表（模块、作用、输入输出形状、参数量），完整 `print(model)` 放附录 C。
   - 标出计算热点候选和对 HCU 可能不友好的算子，例如自动驾驶的 Deformable Attention、spconv、Voxelization、BEV Pooling、NMS；VLA 的 LLM Attention / RoPE、视觉编码器、扩散或 Flow Matching 动作头；世界模型的长序列 Attention、3D VAE。
   - 同时对照 TurboPhysAI 已有能力：`turbo_physai/operators/`（MSDA、MDC、grid_sample、bev_pool、voxelization、sparse_conv、upsample_bilinear_2d、deformable_aggregation）和 `turbo_physai/optimizations/common/` 的 Catalog。模型用到的就在表里注明“已有公共实现”，阶段 02 直接用。
   - 这一步是静态判断，只算“候选”，热点以阶段 03 的 profiling 为准。
2. **数据集（2.2）**：规模、单样本形态、预处理与增强、存储格式和位置。
   - 明确“1 个 sample”的定义，吞吐都按它算。
   - 写明性能测试用真实数据还是合成数据，必须与竞品一致。
   - 预判数据加载会不会成为瓶颈（多相机解码、视频解码、点云处理、CPU 增强、`num_workers`）。
3. **测试环境（2.3）**：让用户在 HCU 和竞品机器上分别运行环境采集脚本，结果放进工作区 `env/`：

   ```bash
   python3 "$SKILL_DIR"/scripts/collect_env.py --md - > <workspace>/env/hcu.md
   ```

   > `collect_env.py` 尚未提供（模板引用的脚本链接为空）。在补上之前，按 2.3 的三张表（硬件、软件、性能相关配置）列出需要的命令（`hy-smi` / `nvidia-smi`、`python -c "import torch; ..."`、`pip list`、关键环境变量），由用户执行后粘贴。

   完整 `pip list` 和环境变量放附录 B。
4. **测试方法（2.4）**：
   - 2.4.1 性能指标：写出公式（吞吐 = global batch size / step 时间；性能比例 = HCU 吞吐 / 竞品吞吐；Peak Memory 统一用 reserved 或 allocated 之一并全文一致）。
   - 2.4.2 精度指标：补全阶段 00 确认的判定标准。
   - 2.4.3 测试方法：warmup 步数和统计区间；HCU 与竞品同代码、同配置、同 batch、同 dtype、同并行策略、同数据；固定随机种子；计时在设备同步之后，**不在 profiler 打开时测速**。
   - 2.4.4 测试约束：只测单机、数据子集、共享集群干扰等。
   - 计时方式优先在训练循环里每步记录墙钟时间并写到文件（例如 `step_metrics/rank-<n>.json`），这样后面每次测速口径一致；需要改训练脚本时只加计时，不动训练逻辑，并在 2.4.3 写明。

## 门禁

- [ ] 2.4.1～2.4.3 写清，sample 定义和计时口径明确。
- [ ] HCU 与竞品环境信息都已采集；不一致的配置项已列出原因。

## 常见问题

- 竞品数据只有公开数字：在 4.3 的“数据来源”标“公开数据”，并核对其 batch、卡数、数据是否与本次一致；不一致的不做比例。

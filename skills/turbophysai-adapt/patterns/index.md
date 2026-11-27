# 优化思路索引

按瓶颈类别查可以套用的手法。每类给出代码信号（在模型源码里能找到的写法）和仓库里的真实案例，读案例时注意它成立的前提。

> 第一版只有索引。每类的详细条目（前提与风险、落地写法、验证方法、试过无效的情况）在后续版本按 `<类别>.md` 补充。
>
> 案例路径：已合入的写仓库路径；未合入的写 PR 编号，用 `git fetch upstream pull/<N>/head:pr/<N>` 取到本地查看，合入后改为仓库路径。
>
> 信号命中只说明“值得看一眼”，是否值得改以阶段 03 的 profiling 为准。

| 思路 | 报告类别 | 对应的 profiling 现象 | 代码信号 | 案例 |
|---|---|---|---|---|
| 去掉主机同步 | 数据加载与 Host 侧 | 调用 `.item()` 等期间 GPU 空闲；step 内有大段空泡 | `.item()`、`.tolist()`、`.cpu()`、`torch.cuda.synchronize`、`nonzero`、布尔掩码索引；GPU 张量被当作 Python int 传给 `linspace` / `repeat` / `view` | GR00T `qwen_position.py`（#41）；LingBot-VLA-V2 `qwen3vl_rope_index_cpu.py`（#40）；OpenWAM `host_async.py`（#27）；LingBot-VA `train_sync.py`（#34）；BEVFusion `parse_losses`（`models/bevfusion/training.py`） |
| 小元数据放 CPU 并缓存 | 数据加载与 Host 侧 | 每步重复的小 kernel 和小 H2D 拷贝 | 每步按形状重算网格、位置编码、mask、anchor；常量张量每步新建 | LingBot-VLA-V2 `rope_fast.py`、`qwen3vl_cache_gridTHW.py`、`flex_head_shared_mask.py`（#40）；FlashOCC `device_buffers.py`（#30）；PointPillars `compiled_anchor_grid.py`（#33） |
| 选择编译边界 | 框架 | launch 小间隙密集；elementwise kernel 占比高；图断或重编译多 | 纯张量计算和 ZeRO / checkpoint / 自定义注意力调用混在一起；动态 shape | `models/bevfusion/compile.py`、`models/bevformer/compile.py`、`models/openvla/compile_fsdp1.py`；LingBot-VLA-V2 `qwen3vl_compile_text.py`（#40）；OpenPI `pi0_compile.py`（#29） |
| 复数运算改实数 | 算子 Kernel | 编译区域里出现回退的复数算子，或图断在 RoPE 处 | `view_as_complex`、`torch.polar`、`.real` / `.imag` | DreamZero `real_rope.py`（#42）；LingBot-VA `rotary.py`（#34）；OpenWAM `ports/dit.py`（#27） |
| 逐元素运算融合 | 算子 Kernel | 大量小的 elementwise / reduction kernel | 先 `.float()` 再 norm 再转回；`x * (1 + scale) + shift`；`x + gate * residual`；手写 RMSNorm | OpenWAM `pointwise.py`、`norms.py`（#27）；LingBot-VA `pointwise.py`、`norms.py`（#34）；DreamZero `CausalWanAttentionBlock.py`（#42） |
| 注意力后端选择 | 算子 Kernel | Attention 类 kernel 耗时高；unpad / pad 相关的拷贝 | 等长 batch 走 varlen 接口；右侧 padding 仍构造 mask；FlexAttention 默认分块参数 | DreamZero `attention.py`（#42）；`models/openvla/skip_fa2_unpad.py`；LingBot-VLA-V2 `video_fa2.py`、`flex_kernel_options.py`（#40）；LingBot-VA `attention.py`（#34） |
| 替换为已有算子或融合实现 | 算子 Kernel | Top kernel 是可替换的通用算子 | 自写的上采样、grid_sample、deformable attention；未开 fused 的优化器 | `turbo_physai/operators/`；`optimizations/common/mmcv/`；`models/openvla/fusedAdamW.py`；OpenPI `fused_adamw.py`（#29）；GR00T `optim.py`（#41） |
| 去掉冗余计算 | 其他 | 某些 kernel 的结果没有被使用 | `repeat_interleave(1)`；分支算了但结果丢弃；重复切换 train / eval | DiT4DiT `cosmos_attention.py`（#28）；DreamZero `skip_unused_vae.py`、`train_mode_cache.py`（#42）；LingBot-VLA-V2 `moge_depth_only.py`（#40） |
| 冻结编码器预先计算 | 其他 | 冻结模块的前向占比高 | `requires_grad_(False)` 或 `eval()` 的 VAE / 文本编码器每步对同样的输入重算 | OpenWAM `cache_vae_latents.py`、`text_store.py`（#27）；DiT4DiT `cosmos_cache.py`（#28） |
| 形状固定与数据管线 | 数据加载与 Host 侧 | 等数据的空闲；变长输入导致重编译 | 变长序列直接进编译区域；解码用不到的列；DataLoader 未开 pin memory / persistent workers | `models/openvla/text_len_bucket.py`；GR00T `fixed_padding.py`（#41）；LingBot-VLA-V2 `fast_hf_query.py`（#40）；`models/bevformer/data.py`；FlashOCC `pin_memory.py`、`persistent_workers.py`（#30） |
| Python 循环改张量运算 | 其他 | Host 侧时间长、GPU 上是大量极小 kernel | 对 batch、box、view 做 for 循环；`torch.unique`；逐元素 scatter | PointPillars `tensorized_assigner.py`、`pillar_scatter.py`、`unique_free_sampler.py`（#33）；`models/bevformer/geometry_sca.py` |
| 内存布局 | 算子 Kernel | 卷积前后有布局转换 kernel | 卷积密集的模块；`permute` + `contiguous` 包围卷积 | LingBot-VLA-V2 `conv3d_channel_last.py`（#40）；OpenWAM `vae_layout.py`（#27） |
| 激活重算策略 | 显存 | 重算带来的额外前向耗时 | `with_cp`、`gradient_checkpointing_enable`、`checkpoint(...)` 全层开启 | OpenPI `gemma_checkpoint_stride.py`（#29）；LingBot-VLA-V2 `ckpt_policy.py`（#40）；FlashOCC `disable_activation_checkpoint.py`（#30） |
| 通信重叠与切分 | 通信 | 未被掩盖的通信占比高；各 rank 起始时间差大 | DeepSpeed ZeRO 配置；FSDP 包装策略；DDP 默认参数 | `models/openvla/fsdp_prefetch.py`；OpenPI `ddp_state.py`（#29）；LingBot-VLA-V2 `split_root_fsdp.py`（#40）；GR00T `zero2_*.py`（#41）；OpenWAM `zero*.py`、`deferred_gather.py`（#27） |
| Python 运行时开销 | 数据加载与 Host 侧 | 周期性的长时间停顿 | 训练中大量长期存活的 Python 对象 | `models/openvla/gc_freeze.py`；DreamZero `Fix_GC.py`（#42） |

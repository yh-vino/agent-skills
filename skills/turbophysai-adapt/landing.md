# 落地规范：把一个 OPT 变成可交付的 Group

阶段 02（适配）和阶段 04（优化）改代码时按本文执行。本文只写“适配一个模型时怎么做决定”，接口细节以仓库文档为准：

- 声明接口：`docs/zh/developer_guide/optimization_declarations.md`
- 配置生成：`docs/zh/developer_guide/optimization_config_generation.md`
- 验证要求：`docs/zh/developer_guide/validation.md`
- 评审要求：`../turbophysai-pr-review/checklist.md`（与本文冲突时以清单为准，并回来修正本文）

## 1. 选落地方式

| 方式 | 何时用 |
|---|---|
| **组件补丁**（默认） | 通过 Catalog 声明运行时替换，不改模型源码；代码在 `turbo_physai/optimizations/` 或 `turbo_physai/operators/` |
| git 补丁（`model_examples/<Model>/*.patch`） | 只在组件补丁做不到、且团队同意时使用；用之前先按第 6 节确认是不是引擎能力缺口 |

下面各节都针对组件补丁。

## 2. 选代码位置：先复用，再写公共，最后写模型专用

按顺序判断，命中就停：

1. **公共件已有同功能** → 不写代码。模型 recipe 用 `extends` 引入对应公共配置，或在 `optimization_groups` 里启用该 Group。
2. **另一个模型已替换过同一个框架入口**（`grep -rn "<target>" turbo_physai/optimizations/models/*/catalog.py`）→ 不另写一份。把两边合成一份公共实现放进 `common/<framework>/`，两个模型都改为引用它。维护者已计划自己统一的重复（如各模型的 fused AdamW）除外，先问用户。
3. **满足公共件三个条件** → 写进 `turbo_physai/optimizations/common/<framework>/`：
   1. 目标是框架或库入口（`torch`、`transformers`、`diffusers`、`deepspeed`、`mmcv`、`mmdet`、`mmdet3d` 等），不是模型仓库自己的代码（如 `projects.*`、`groot.*`）；
   2. 实现不读取模型特有的属性、配置、数据字段，不对 shape 做只有该模型满足的假设；
   3. 对该入口的任何调用方都等价，不改变训练 recipe。

   公共件的额外要求：
   - 要让其他模型、其他库版本也能直接生效：声明时 `collect_target_hash=False`，适用性靠 `runtime_condition`（逐次调用判断）和 `compatibility_check`（版本、签名等一次性判断）保证，不满足时回退原实现；
   - 必须有单测（第 5 节）；
   - 数值会变的设为默认关闭，或标 `accuracy_only`。
4. **以上都不满足** → 写进 `turbo_physai/optimizations/models/<model>/`。

## 3. 模型目录结构

```
turbo_physai/optimizations/models/<model>/
  __init__.py
  catalog.py               只放声明（group / replace / wrap），只写字符串路径，导入时不导入模型或 torch
  <topic>.py               Replacement 与 Wrapper Factory，按优化主题分文件
  configs/
    __init__.py
    recipe.yaml            人工维护：metadata、optimization_modules、extends、optimization_groups、options
    optimization.yaml      CLI 生成，不手改
    .optimization.yaml.generation.json   CLI 生成
    runtime.yaml           只在确需固定环境变量时提供
```

已合入的 `models/bevformer`、`models/bevfusion`、`models/openvla` 是参照样板。

## 4. Group 设计

- **一个 Group 是一项可以独立检查、应用、回滚的完整优化。** 缺一不可的成员放同一个 Group，能拆开的不放一起。OPT 与 Group 可以一对多、多对一，但每个 Group 都要能用 `--disable-group` 单独关掉，用于测单项收益和排查问题。
- **Group ID**：`<model>.<领域>.<名称>`（公共件为 `<framework>.<名称>`），如 `openvla.adamw.fused`、`bevfusion.compile.fuser`。已有 Group ID 不改名。
- **默认解耦**：单独开关任一 Group 都要能正确工作。不要在一个 Group 的实现里导入另一个 Group 的实现、共享模块级状态或依赖它先安装；很多“依赖”其实是漏了 alias。确实不能解耦的，三处都要写：Catalog 里 `depends_on`；recipe 里 `extends` 被依赖的公共配置；生成的配置里依赖闭包完整、顺序正确。
- **`replace` 还是 `wrap`**：整体换掉实现用 `replace`；保留原对象、在外层加编译、输入转换、参数调整用 `wrap`。`wrap` 的 Factory 只负责构造包装函数，计算放在包装函数里。原模块能导入时不用 `replace_import`；导入兼容声明不和普通 `replace` / `wrap` 放进同一个 Group。
- **替换尽量小**：改动只落在某个子函数或方法里时，就替换那个子函数；只在调用前后加处理时用 `wrap`。不整份复制上游文件，复制时不带进不替换的内容和样板。
- **alias**：目标被 `from x import y` 提前引用的路径都要声明进 `aliases`，否则部分调用点替换不到。用 `grep -rn "import <name>" <模型仓库>` 找。
- **适用条件**：
  - `runtime_condition`：只对部分输入成立时用，必须轻量、确定、无副作用、返回 `bool`；两个分支都要验证。
  - `compatibility_check`：基础检查（类型、签名、源码哈希）覆盖不了的版本、ABI、私有接口前提才加，只读。
  - 依赖私有接口、编译器生成代码或只在特定版本、shape、硬件下成立的优化：前提用上面两者检查，不满足时回退原实现，不报错、不静默算错。
- **`options`**：只有 Replacement 确有可配置行为时才加，字段、类型、默认值写进模型 README。
- **`accuracy_only`**：会改变数值的优化（TF32、非确定性算法、近似计算）在 recipe 里标记，只在 `turbo-physai run --accuracy` 时应用，精度影响写进 OPT 小节。
- **torch.compile**：所有调用 `torch.compile` 的 wrap 在 `TURBO_PHYSAI_DISABLE_TORCH_COMPILE=1` 时返回原实现，不另设开关。
- **不在 Group 机制外改变训练行为**：不写替代上游 `train.py` 的入口脚本、`sitecustomize.py`、往 `PYTHONPATH` 注入目录、启动前改上游对象。这些关不掉，也不出现在 OptimizationReport 里。确实需要的，按第 6 节处理。
- **原生算子**：需要编译的 `.cu` / `.cpp` 按 `docs/zh/developer_guide/custom_operator.md` 放 `kernel/<op>/`，编进 `turbo_physai._C`，通过 `operators/` 的 Python 前端给 Group 用；不在运行时用 `cpp_extension.load` 现场编译。
- **多卡一致性**：需要各 rank 一致的值（随机数、时间步、失败标记）要同步；缓存键覆盖所有会变化的输入。

## 5. 配置、运行与验证

```bash
# 1. 生成配置（模型仓库工作区干净，HEAD 等于接入基线 commit）
turbo-physai optimization generate --recipe <recipe.yaml> --repo <模型仓库> \
    --commit <接入基线 commit> --output <configs/optimization.yaml> [--force]
turbo-physai optimization check --generated-only <configs/optimization.yaml>

# 2. 运行并确认生效（在模型仓库里，上游官方命令前加 turbo-physai run）
turbo-physai run --optimization-config <configs/optimization.yaml> --log-report <上游官方训练命令>

# 3. 测单项收益：关掉本 OPT 的 Group 做对照
turbo-physai run --optimization-config <...> --disable-group <group_id> <上游官方训练命令>

# 4. 应用 accuracy_only 的 Group
turbo-physai run --optimization-config <...> --accuracy <上游官方训练命令>
```

- 修改 Catalog 或 recipe 后必须重新生成配置；`optimization.yaml` 不手改。
- 哈希不匹配导致 Group 被阻断时，不要用 `--force-group` 绕过来交付：要么在正确的基线 commit 上重新生成，要么说明版本差异并交给维护者判断。
- 单测按 `validation.md`：计算改写对比输出和必要梯度（固定种子，写明容差）；`runtime_condition` 两个分支、`compatibility_check` 兼容与不兼容两种情况都测。只有算子、公共优化和引擎要求单测；模型专用优化至少在本地做数值对比，结论写进 OPT 小节。
- 每个 OPT 合入后先确认 `--log-report` 里新 Group 为 `applied`、其他 Group 状态不变，再做快速精度检查，最后测速。

## 6. 引擎做不到时

以下情况普通 Group 处理不了，属于引擎能力缺口：模型在模块导入时就出错（导入时现场编译扩展）；目标在作为 `__main__` 运行的启动脚本里；引擎读不了的源码（非 UTF-8）导致哈希缺失；同一对象既要改实现又要加 wrap（只能合进一个 Replacement）。

处理方式：先按 `docs/zh/design/execution.md` 的应用顺序（导入兼容 Group → 解析全部普通目标 → 安装替换）确认现有机制确实做不到；然后用最小的绕法完成本模型，在 README、PR 描述和代码 TODO 里写明改变了什么、为什么必须；同时把引擎侧的补法（新增什么声明或能力、在哪个阶段生效、怎么回滚和报告）记成一条 ISSUE，引擎改动单独提 PR。

## 7. 记录

- `state.json`：OPT 的 `groups` 写交付的 Group ID，`location` 写 `common` / `models/<model>` / `git-patch`。
- 优化报告 OPT 小节的“实现方案”写 Group ID、开关（`--disable-group <id>`）、相关环境变量和代码 commit。
- 性能数字只写在优化报告里，不写进代码注释、commit message、README 和 PR 描述。

# TurboPhysAI 模型适配 PR 检查清单

评审（`turbophysai-pr-review`）和提交前自检（`turbophysai-pr-selfcheck`）共用这份清单，改规则只改这里。

标记：**[git 补丁]** 改动包含 `model_examples/<Model>/*.patch`；**[组件补丁]** 改动包含 `turbo_physai/optimizations/` 或 `turbo_physai/operators/`。两种都有时两类都查；不带标记的为通用项。

分级：**必须修改**（影响正确性、违反仓库约定、有平台风险）/ **建议修改**（冗余、过度设计、可迁入公共优化等）/ **询问**（拿不准是否必要，或需要作者说明）。只提有实际影响的问题，不提流程性要求（给所有依赖钉版本、要求 SHA256、提醒许可条款）和 lint 能查出的问题。

## A. 正确性（必须修改）

1. 多卡一致性：需要各 rank 一致的值（随机数、时间步、失败标记）是否同步；集合通信的异步/回退路径是否等价。
2. 形状和维度假设：维度顺序、维度数，批量、多视角等情况下是否成立。
3. 缓存：缓存键是否覆盖所有会变化的输入，输入变化后会不会用到旧结果，并发是否安全。
4. 执行顺序：hook、初始化、加载、更新的先后是否正确，改动在实际顺序下是否真的生效（如“第一步前”还是“第一步后”）。
5. 条件和回退分支：条件是否过宽或过窄；异常是否被吞掉；探测失败不能当成否定结果（“不知道”和“确认没有”要区分，调用方 `if not f()` 会把 `None` 当成 `False`）；HCU 门控是否正确。
6. 精度：精度由内部文档保证，不做精度验证、不要求对比数据，只检查 PR 描述是否写明已做精度验证；没写的作为询问。

## B. [组件补丁] Group 与声明

依据 `docs/zh/developer_guide/optimization_declarations.md`：

1. 调用契约：Replacement 保持目标的参数、返回值、shape、dtype、device 和梯度；`wrap` 的 Factory 只构造包装函数，计算放在包装函数里。
2. Group 边界：缺一不可的成员在同一 Group，能独立检查、应用和回滚；能拆开的不放一起；已有 Group ID 不随意改名。
3. Group 之间默认解耦：单独启用或关闭任一 Group 都能正确工作。查隐式耦合：Replacement 直接导入或调用另一个 Group 的实现、共享模块级状态、依赖另一个 Group 先安装。很多“依赖”其实是漏了 alias（见第 5 项），补上即可解除。确实不能解耦的，依赖要在完整链路上逐环明确，缺任何一环都是必须修改：
   - Catalog：依赖方 Group 用 `depends_on` 声明被依赖的 Group ID；
   - Recipe：被依赖的公共 Group 所在的公共配置在 `extends` 里（模型 Replacement 引用公共 Replacement 时也必须如此）；
   - 生成的 `optimization.yaml`：依赖闭包完整，被依赖的 Group 排在依赖方前面。
4. 声明方式：`replace` / `wrap` 选择得当；原模块能导入时用对象级 `replace`，不用 `replace_import`；导入兼容声明不和普通 `replace` / `wrap` 混在一个 Group。
5. Alias：目标被 `from x import y` 提前引用的路径都声明了 `aliases`，否则部分调用点替换不到。
6. `runtime_condition` 轻量、确定、无副作用并返回 `bool`；`compatibility_check` 只读，且只在基础检查覆盖不了时才加；`options` 只在 Replacement 确有可配置行为时加，并在文档里说明。
7. 不绕过 Engine 的目标检查、冲突分析、执行顺序或回滚机制来处理单个模型问题。
8. 不在 Group 机制外改变训练行为：自定义入口（替代上游 `train.py` 的 `entry.py`）、`sitecustomize.py`、往 `PYTHONPATH` 注入目录、启动前修改上游对象等，无法用 `--disable-group` 关闭，也不出现在 OptimizationReport 中。能做成 Group 的做成 Group；确实需要的，README 和 PR 描述写明它改变了什么、为什么必须。
9. 引擎能力缺口：判断“绕过 Engine”之前，先按 `docs/zh/design/execution.md` 的应用顺序（导入兼容 Group → 解析全部普通目标 → 安装替换）确认现有机制能否做到。典型缺口：模型在模块导入时就出错（导入时现场编译扩展），普通 Group 来不及拦截；目标在作为 `__main__` 运行的启动脚本里；引擎读不了的源码（非 UTF-8）导致哈希缺失；同一对象既要改实现又要 wrap（如再加 compile），只能合在一个 Replacement 里。这类不要求模型 PR 删掉绕法，要求在 README、PR 描述和代码 TODO 里写明；评审评论里给出引擎侧的补法（新增什么声明或能力、生效阶段、回滚和报告方式）和迁移后模型侧能删掉什么，引擎改动单独提 PR。
10. 原生算子：模型目录里自带、需要编译的 `.cu`/`.cpp`（含改过的第三方 kernel）属于算子，按 `docs/zh/developer_guide/custom_operator.md` 放 `kernel/<op>/` 编入 `turbo_physai._C`，经 `operators/` 的 Python 前端供 Group 使用；不在运行时用 `cpp_extension.load` 现场编译，不定义独立 `PYBIND11_MODULE`。模型仓库自带、未修改的扩展属于模型安装步骤，参照 BEVFusion 用上游安装命令编译，不算 TurboPhysAI 算子。
11. 依赖框架内部实现的优化（私有接口、编译器生成的代码、内部命名，或只在特定版本、shape、硬件下成立）：不要求删除，查前提变化时是否安全：前提用 `compatibility_check` / `runtime_condition` 检查，不满足时回退原实现，不报错也不静默算错；适用范围写进 PR 描述。需要新增引擎能力才能做的按第 9 项处理。
12. compile：所有调用 `torch.compile` 的 wrap 都要在 `TURBO_PHYSAI_DISABLE_TORCH_COMPILE=1` 时返回原实现，不另设开关（见 `docs/zh/user_guide/troubleshooting.md` 第 8 节）。

## C. 冗余与过度设计（默认建议修改，影响维护或有平台风险时升为必须修改）

原则：保证功能的前提下尽量简单。代码、README、脚本、requirements、测试都要看。

1. 冗余：同一处理、说明、环境变量、依赖只出现一处；调试代码、注释掉的代码、仅为开发者方便的工具删掉。死代码（异常被吞掉导致永远不生效、永远走不到的分支）按询问处理：确认是否必要，不必要就删掉，必要就修好。默认关闭、用途明确的辅助 Group（如可复现性、数据对齐）可以保留。Engine 公共测试已覆盖的机制（声明校验、应用、阻断、回滚、报告）不在优化测试里重复写。
2. 过度设计：只用一次的逻辑不加抽象、配置项或开关；能用现有机制（上游已有的、TurboPhysAI 已有的）的不另起一套。
3. 侵入最小：只改 HCU 适配和优化必需的部分；不整份复制上游或第三方文件，只覆盖需要改的方法（继承、方法级替换、`wrap`、只在 HCU 启用）。替换一个对象就要复制它的完整实现再改，这部分不提。只提三种情况：复制了不替换的内容（整个文件、整个类、无关函数）；有更小的目标可替换（改动只落在被调用的某个子函数或方法里，或只是在调用前后加处理、能用 `wrap`）；复制时带进的样板（每个文件重复的 import、原样搬来的大段 docstring 和注释）。
4. 写法、命名与上游及已合入模型一致；可配置的值不硬编码。

## D. 仓库约定

1. **跟随上游官方流程**（必须修改）：数据、权重来源和版本、数据准备、训练 recipe 与上游一致，官方命令保持不动。只有 HCU 相关部分（镜像、补丁应用或 `turbo-physai run`、环境变量、HCU 必需的参数调整，单独列出即可）可以不同。私有下载地址、无说明的 recipe 改动属于必须修改。
   - 不只看上游 README，要找到官方启动脚本（如 `examples/*/train_files/run_*.sh`、`scripts/*.sh`）和数据下载脚本，把 README 的命令与之逐项比对：入口、每个参数、参数缺失时 yaml 里的默认值。重点查会改变训练 recipe 的参数（冻结模块、学习率、warmup、batch、梯度累积、loss 配置）。
2. **快速验证**：可作为可选附加流程，自定义命令只放在这部分；所用数据子集要能从官方数据用脚本生成，README 写清生成命令，不能以下载私有压缩包为唯一途径。
3. **路径**：没有开发机路径、内网地址、虚构的默认路径；用一个根目录变量拼接其他路径；同一份数据在各处路径一致。
4. **说明文档**（`model_examples/<Model>/README.md`）：新模型必须有，以 main 上已合入模型（BEVFormer、BEVFusion、OpenVLA）的 README 为参照。共有部分：
   - 模型简介、接入基线（上游仓库地址 + 固定 commit）；
   - 镜像和 TurboPhysAI 安装：只用安装指南（以上游 main 的 `docs/zh/get_started/installation.md` 为准）“使用配套镜像”一节列出的两类配套镜像，一类给自动驾驶模型，一类给 VLA、DiT 和世界模型。README 开头写一句：请先按照[安装指南](../../docs/zh/get_started/installation.md#使用配套镜像)，使用<自动驾驶 / VLA>配套镜像创建容器并安装 TurboPhysAI。README 里不重复写镜像地址、`docker pull`/`docker run` 和 TurboPhysAI 的构建安装命令；需要未发布的修改时链接指南的从源码安装一节。自己写了这些内容、或者用了配套镜像以外的镜像，属于必须修改；
   - 准备模型源码（克隆上游并检出基线 commit）、安装依赖；`pip`/`python` 用与安装指南相同的解释器；
   - 数据和权重：给出官方来源和准备方式（同第 1、2 项）；
   - 启动训练：按交付范围给出命令，并说明如何确认优化已生效；
   - 格式：代码块缩进、列表等渲染正确，按顺序执行能从头走通。

   按方式不同的部分：**[git 补丁]** 写明补丁应用步骤，训练命令即上游官方命令；**[组件补丁]** 不改模型源码，训练命令是在上游官方命令前加 `turbo-physai run`，并说明自定义配置时如何用 `--optimization-config` / `--runtime-config` 指定。
5. **依赖清单**：镜像已包含模型训练依赖时不用提供（如 BEVFormer、BEVFusion）。镜像缺依赖，且直接 `pip install -e .` 会覆盖 HCU 专用包（如 DTK 版 torch）或上游钉住的版本与 HCU 验证版本不一致时，在 `model_examples/<Model>/requirements.txt` 提供清单：以上游依赖为基础，去掉镜像已提供的包，与上游一致的照抄，不一致的写实测版本并在行尾注释原因；不修改上游的 `pyproject.toml`。README 安装步骤按需：模型直接在源码目录运行时不需要；需要安装模型时用 `pip install -e . --no-deps`；镜像缺依赖时再加 `pip install -r <TurboPhysAI 仓库>/model_examples/<Model>/requirements.txt`。
6. **支持列表**（`docs/zh/models/support_list.md`）：新模型有条目；标为已支持的任务，PR 描述里要写明已验证；基线 commit 与 README 一致。
7. **第三方声明**（`THIRD_PARTY_NOTICES.md`）：修改或复制进来的上游/第三方代码都要列出，包括文件里只有一部分改写自第三方的（看文件内的 `derives from` / `Adapted from` 注释）；只列有实质修改的文件。声明和文件头里引用的 commit、tag 要能在上游公开仓库查到（`gh api repos/<owner>/<repo>/commits/<sha>`，422 即不存在），并与接入基线一致。**[git 补丁]** 用 `check_patch.sh` 输出的文件清单比对。
8. **平台影响**：对通用路径的改动只在 HCU 下生效，或说明对其他平台无影响；通用逻辑与 HCU 专用逻辑分开。还要查行为变化：是否新增报错路径、原来会照常运行的情况现在是否失败、回退行为是否改变。有的话，`docs/zh/` 对应文档写明触发条件和用户的处理办法（关闭开关、手动配置等）。
9. **优化**：适配和优化是这类 PR 的目的，不要求删掉优化，只按 C 节要求侵入最小。其他方向（如把优化做成新的公共算子）作为后续建议，不作为本 PR 的要求。
10. **无关改动**：与该模型无关的改动建议单独提 PR。
11. **PR 描述**与当前提交一致，包含：
    - 做了哪些修改、分别解决什么问题：每个新增 Optimization Group 各优化什么；模型目录以外的每项改动各解决什么问题；
    - 已执行的测试命令和结果：单元测试（注明哪些在 HCU 上跑）、生成和文档检查、README 训练命令在 HCU 上的实际运行情况（跑了多少步，`--log-report` 中各 Group 是否都已应用）；
    - 是否做过精度验证（见 A 第 6 项）；
    - 未完成的验证。

    不写性能数据（步时、加速比、基线对比），评审也不索要。

**[组件补丁]** 另查：

12. **目录**：与模型无关且入口稳定的放 `turbo_physai/optimizations/common/<framework>/`，依赖模型结构、数据链路或训练过程的放 `turbo_physai/optimizations/models/<model>/`（见 `docs/zh/developer_guide/optimization_workflow.md`）。模型目录下的每个 Group 都要判断能否放入公共优化，同时满足以下条件才算：
    1. 目标是框架或库的入口（`torch`、`mmcv`、`mmdet`、`mmdet3d`、`transformers` 等），不是模型仓库自己的代码（如 `projects.*`）；
    2. 实现不读取模型特有的属性、配置项、数据字段，也不对 shape 做只有该模型才满足的假设；
    3. 对该入口的任何调用方行为都等价，不改变训练 recipe。

    判断时到 `optimizations/common/` 和其他模型的 Catalog 里 grep 同一目标、同类实现（如 DataLoader 的 pin memory / persistent workers、关闭 activation checkpoint）。分级：
    - 公共优化里已有同等功能，或另一个模型已经替换了同一框架入口，PR 却另写一份：必须修改，改为复用（模型 Recipe 用 `extends` 引入公共配置），或合并成一份公共实现。维护者已计划自己统一的重复（如各模型的 fused AdamW）不在单个模型 PR 里提；
    - 满足条件但目前只有这一个模型用到：建议修改，说明满足哪几条、建议迁到哪个 `common/<framework>/` 目录。迁入后要按第 14 项补公共优化测试，写明这项成本，由作者决定在本 PR 里做还是后续再做；
    - 不满足的，不提，但在“已检查的项”里一句话说明原因（如目标在 `projects.*`、依赖模型的 grid 配置）。
13. **配置**：`optimization.yaml` 由 CLI 生成、没有手改；模型配置记录的 commit 与 README 的接入基线一致；只有确需固定环境变量时才有 `runtime.yaml`。
14. **测试**：只要求覆盖算子（`turbo_physai/operators/`）、公共优化（`turbo_physai/optimizations/common/`）和引擎，模型专用优化不要求补测试。适用范围内的改动按 `docs/zh/developer_guide/validation.md`：计算改写有输出和必要梯度与参考实现的对比（固定种子，写明容差）；`runtime_condition` 两个分支、`compatibility_check` 兼容与不兼容场景都有测试；明确不需要梯度的输入在实现和测试里说明。
15. **文档同步**：接口、CLI 或配置格式变动时，`docs/zh/` 下的对应指南和参考文档同步更新。

---
name: integrate-dasdriving-optimization
description: Develop, package, generate a ModelPlan for, and validate model or backend-operator optimizations with dasDriving. Use when Codex needs to initialize an external optimization project, compare baseline and optimized model code, implement Replacement functions or wrappers, declare group/replace/wrap catalogs, split atomic optimization Groups, generate or check ModelPlan YAML, run correctness and HCU smoke tests, diagnose PatchReport results, or prepare a validated optimization for long-term inclusion in dasDriving.
---

# Integrate dasDriving Optimization

## Objective

Guide an optimization from experimental code to a reproducible dasDriving
delivery without requiring the developer to learn framework internals.

Keep the developer-facing model small:

1. Implement the optimized behavior.
2. Declare the target, Replacement, aliases when known, and atomic Group.
3. Select Groups in a minimal Plan template.
4. Generate, check, apply, and validate the final ModelPlan.

## Establish the working context

Before editing:

1. Locate the installed dasDriving package or source repository.
2. Locate the unmodified model baseline and record its Git commit.
3. Locate the optimized reference, diff, or performance goal.
4. Confirm the target runtime, device, launch command, and available tests.
5. Inspect the current CLI help and repository documentation instead of assuming
   commands or schema fields from an older framework version.

Preserve the model baseline unless the user explicitly asks to modify it. Develop
new optimizations in an external project first; change dasDriving framework code
only when a minimal reproduction proves a general framework gap.

## Follow the integration workflow

### 1. Initialize an external project

Use the installed CLI:

```bash
python -m das_driving.cli optimization init <model-name> \
  --output <external-project-directory>
```

Run from the generated project directory or install it editable so the module in
`optimization_modules` is importable. Read
[references/developer-workflow.md](references/developer-workflow.md) for the
generated layout and command sequence.

### 2. Build an optimization map

For every change, record:

- original Python target;
- optimized implementation;
- expected inputs, outputs, dtype, shape, device, and gradients;
- known aliases;
- whether it requires model-specific context;
- which other changes are required for the feature to be complete;
- environment or launch requirements;
- correctness and performance evidence.

Classify the change before declaring it:

- Accept a public capability only when it is an independently validated,
  model-independent backend operator replacement with a stable entry point.
- Keep model Forward rewrites, data pipelines, tensor-layout chains, compile
  regions, and training configuration in model-specific Groups.

Do not infer semantic containment by scanning function bodies. Resolve declared
target conflicts explicitly.

### 3. Implement Replacement code

Preserve the external calling contract. Adapt an incompatible lower-level kernel
inside the Replacement rather than changing the model caller.

Do not silently catch an optimized-path failure and execute the original
implementation. Raise a clear Python exception from a named dasDriving
Replacement so the traceback identifies the failing component.

Keep Catalog modules declarative and import-light. Put Torch, HCU, hipDNN,
LightOp, MMCV, and model imports in implementation modules or runtime call paths.

### 4. Declare optimization Groups

Use only the developer API:

```python
from das_driving import group, replace, wrap
```

Use `replace` when the optimized object fully replaces the target. Use `wrap`
when a factory needs the original object and returns a new object.

Define one Group as one independently meaningful feature: if any member is
missing, the feature is incorrect or incomplete. Add `depends_on` only when the
current Group is not correct without another Group.

Read [references/declaration-rules.md](references/declaration-rules.md) before
creating or revising a Catalog.

### 5. Select Groups and generate the final Plan

Edit only the minimal template:

- Plan identity and model name;
- `optimization_modules`;
- inherited public Plan IDs;
- selected Group IDs and `enabled`;
- `options` only when a Wrapper consumes them.

Do not hand-write target hashes, AST hashes, dependency closure, or final
compatibility commit evidence.

Generate the final YAML from a clean model repository at the validated commit:

```bash
python -m das_driving.cli plan generate \
  --template <template.yaml> \
  --repo <model-repository> \
  --commit <validated-commit> \
  --output <final-model-plan.yaml>
```

Treat a generation conflict as a development error. Modify the template,
Catalog boundary, or Replacement and regenerate; never rely on registration
order or last-wins behavior.

### 6. Check before application

Use each check for its actual purpose:

```bash
# Schema, optimization_modules, and extends.
python -m das_driving.cli plan validate <plan.yaml>

# Existing final YAML against the current clean model repository.
python -m das_driving.cli plan check <plan.yaml> --repo <model-repository>
```

Use `das_driving.check(plan_path=...)` for runtime applicability and decisions.
It does not install replacements, but it can import target and Replacement
modules and construct Wrappers. Require Wrapper construction to avoid
irreversible side effects.

### 7. Apply and validate incrementally

Call `das_driving.apply()` once per process and before importing the target model:

```python
import das_driving

report = das_driving.apply(
    plan_path="./plans/model.yaml",
    report_dir="./dasdriving_reports",
)

from project.train import main
main()
```

Validate one Group, then cumulative Groups, then the full Plan. Compare numerical
results, required gradients, runtime behavior, performance, memory, and compile
stability against the baseline and optimized reference.

Read [references/validation-checklist.md](references/validation-checklist.md)
before claiming completion.

### 8. Prepare handoff

Return:

- files created or changed;
- a table of Groups, members, targets, and functional boundaries;
- public versus model-specific classification;
- generated Plan path and supported model commit;
- checks and tests actually run;
- numerical and performance evidence;
- environment and launch requirements;
- blocked items, known limitations, and framework gaps;
- PatchReport paths from the final smoke test.

Move a stable optimization into the dasDriving repository only after it passes
external development, correctness, real-model, and performance review.

## Enforce current framework boundaries

- Do not use legacy `Patcher`, `Patch`, or `AtomicPatch` for new integration.
- Do not call `apply()` twice or retry it in the same process.
- Do not treat a successful installation report as proof that later training
  execution is correct.
- Do not use `force_groups` for formal delivery; reserve it for reviewed,
  one-time debugging of overrideable evidence checks.
- Do not claim that a matching target Hash automatically overrides a model
  commit mismatch. The current checker treats them as independent checks.
- Do not add `runtime_environment` to ModelPlan until the installed schema
  supports it. Record environment variables in the migration launch assets;
  current `apply()` does not manage or roll them back.
- Do not promote model-specific behavior to the public Plan. The current public
  acceptance boundary is independently validated backend operator replacement.

## Route detailed questions

- Read [references/developer-workflow.md](references/developer-workflow.md) for
  project layout, Plan lifecycle, CLI commands, and startup order.
- Read [references/declaration-rules.md](references/declaration-rules.md) for
  `replace`, `wrap`, Group atomicity, aliases, dependencies, and conflicts.
- Read [references/validation-checklist.md](references/validation-checklist.md)
  for correctness, framework, HCU smoke, performance, reporting, and handoff
  gates.

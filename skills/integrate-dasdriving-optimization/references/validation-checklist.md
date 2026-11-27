# dasDriving optimization validation checklist

## Contents

1. Baseline and repository
2. Replacement correctness
3. Catalog and framework behavior
4. Plan generation
5. Runtime smoke
6. Performance
7. Report and handoff

## 1. Baseline and repository

- [ ] Record the official model commit.
- [ ] Record the optimized reference commit or diff.
- [ ] Keep the baseline worktree clean.
- [ ] Record the dasDriving version or commit.
- [ ] Record the HCU image, dependency versions, device count, and launch
      command.
- [ ] Separate model-source changes from external integration changes.

## 2. Replacement correctness

- [ ] Compare Forward outputs with fixed inputs, weights, and random seeds.
- [ ] Compare every gradient required by the real model.
- [ ] State explicitly when an input does not require a gradient.
- [ ] Cover supported dtype, shape, device, optional arguments, and modes.
- [ ] Verify caller-facing signature compatibility.
- [ ] Verify unsupported configurations raise a clear dasDriving or external
      optimization error.
- [ ] Verify no exception path silently falls back to the baseline.
- [ ] Verify traceback contains the Replacement module path.

For compiled regions:

- [ ] Exercise every actual Python branch, including `if/else`, `None/non-None`,
      train/eval, and relevant shape changes.
- [ ] Inspect `TORCH_LOGS=recompiles` after warm-up.
- [ ] Check that compile construction does not mutate global state during
      `das_driving.check()`.

## 3. Catalog and framework behavior

- [ ] Import the Catalog without importing Torch/HCU/model implementation
      modules when possible.
- [ ] Verify every target and Replacement path resolves.
- [ ] Verify each declared alias is the same original object.
- [ ] Confirm Group membership matches functional atomicity.
- [ ] Confirm `depends_on` represents correctness, not preference.
- [ ] Confirm Group registration is complete and conflict-free.
- [ ] Inject one member failure and verify complete Group rollback.
- [ ] Verify rollback failure is surfaced as terminal when testing the general
      framework path.
- [ ] Verify blocked or failed Groups stop only their dependents.

## 4. Plan generation

- [ ] Keep the template minimal and human-maintained.
- [ ] Generate from the validated clean model commit.
- [ ] Resolve all Group and target conflicts before YAML is written.
- [ ] Confirm public and dependency Groups are expanded as intended.
- [ ] Run `plan validate` on the output.
- [ ] Run `plan check --repo ...` on the output.
- [ ] Confirm the final YAML and Catalog version are delivered together.
- [ ] Regenerate after target, alias, Replacement path, Group membership, or
      dependency changes.

Do not claim that the Plan hashes the Replacement or Kernel implementation.
Current trust evidence binds model targets.

## 5. Runtime smoke

Run in a new process with `apply()` before model imports:

```text
single Group
→ cumulative Groups
→ complete ModelPlan
→ fixed-input comparison
→ first training iteration
→ warm-up iterations
→ stable measured iterations
```

- [ ] Confirm the expected Groups are `applied`.
- [ ] Confirm no unexpected `blocked`, `failed`, `rolled_back`, or
      `not_started` results.
- [ ] Confirm loss and representative gradients remain acceptable.
- [ ] Confirm errors after `apply()` are tested separately; PatchReport does not
      capture later training exceptions automatically.
- [ ] Restart the process between apply attempts.

For distributed smoke, use the normal launcher so child ranks inherit the same
validated launch environment. Do not add cross-rank framework logic unless a
real failure requires it.

## 6. Performance

- [ ] Use the same dataset, batch size, precision, device visibility, NUMA
      binding, and profiler settings for baseline and optimized runs.
- [ ] Separate compile warm-up from steady-state measurement.
- [ ] Compare median iteration time rather than one iteration.
- [ ] Compare peak memory.
- [ ] Inspect the expected profiler hotspots.
- [ ] Confirm the optimization is actually executed, not merely installed.
- [ ] Record environment variables and startup options needed for reproduction.

Do not invent a universal tolerance. Use the model's accepted numerical and
performance thresholds and state them in the test record.

## 7. Report and handoff

Collect:

- final ModelPlan YAML;
- external optimization package or dasDriving source changes;
- optimization map and Group table;
- unit and integration test results;
- smoke logs;
- JSON and Markdown PatchReport;
- performance/profiler comparison;
- environment and launch requirements;
- unsupported cases and known limitations.

Classify handoff:

- **External development only**: correctness or performance still under review.
- **Model capability**: validated but tied to one model context.
- **Public backend operator**: independently validated, stable backend entry,
  model-independent, and suitable for a public base Plan after maintainer
  review.

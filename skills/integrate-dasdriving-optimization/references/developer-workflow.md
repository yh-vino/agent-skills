# dasDriving optimization developer workflow

## Contents

1. Source-of-truth checks
2. External project layout
3. Development sequence
4. ModelPlan lifecycle
5. Runtime application
6. Current limitations

## 1. Source-of-truth checks

Prefer the installed version's output:

```bash
python -m das_driving.cli --help
python -m das_driving.cli optimization init --help
python -m das_driving.cli plan generate --help
python -m das_driving.cli plan check --help
```

When a source checkout is available, inspect these files before changing a
workflow:

```text
das_driving/__init__.py
das_driving/cli.py
das_driving/development/scaffold.py
das_driving/patcher/declarations.py
das_driving/patcher/engine.py
das_driving/patcher/plans/schema.py
das_driving/patcher/plans/generator.py
```

Do not assume an unimplemented field or command exists because it appears in a
design discussion.

## 2. External project layout

Initialize:

```bash
python -m das_driving.cli optimization init bevformer \
  --output ./bevformer_optimization
```

Current scaffold:

```text
bevformer_optimization/
├── README.md
├── pyproject.toml
├── bevformer_optimization/
│   ├── __init__.py
│   ├── catalog.py
│   └── replacements.py
├── plans/
│   └── bevformer.template.yaml
└── tests/
    └── test_catalog.py
```

The initial template imports the external Catalog, inherits
`backend.hcu.base`, and selects no model Groups. The public base Plan is
currently empty until backend operators pass independent validation.

Make the external package importable by running commands from the project root
or installing it:

```bash
python -m pip install -e .
```

## 3. Development sequence

Use this order:

```text
baseline and optimized diff
→ optimization map
→ Replacement implementation
→ numerical and gradient tests
→ Catalog Group declaration
→ minimal Plan template selection
→ Plan generation
→ runtime check
→ single-Group smoke
→ cumulative smoke
→ full performance validation
```

Keep the model baseline repository unchanged. Store integration code, tests,
plans, dependencies, and launch assets in the external optimization project.

When a general framework defect appears:

1. Reduce it to a pure-Python or minimal fake-module reproduction.
2. Add a framework regression test.
3. Propose the general fix separately from the model Replacement.
4. Re-run the affected model Group after the framework fix.

## 4. ModelPlan lifecycle

### Minimal template

Maintain only developer decisions:

```yaml
api_version: dasdriving/v1alpha1
kind: ModelPlan

metadata:
  id: model.customer.development.hcu
  version: "0.1.0"
  description: Customer optimization development plan

model:
  name: Customer

optimization_modules:
  - customer_optimization.catalog

extends:
  - backend.hcu.base

compatibility: {}

patch_groups:
  - id: customer.encoder
    enabled: true
```

Keep `depends_on` in the Catalog. Keep target and Replacement paths in the
Catalog. Let the Generator write commit, source Hash, AST Hash, and dependency
closure.

### Generate the final YAML

Require a clean repository whose `HEAD` equals the supplied commit:

```bash
python -m das_driving.cli plan generate \
  --template plans/customer.template.yaml \
  --repo /path/to/CustomerModel \
  --commit <validated-commit> \
  --output plans/customer.yaml
```

Use `--force` only when intentionally replacing an existing generated output.

Generation:

```text
validates the template
→ loads optimization_modules
→ expands extends
→ expands depends_on closure
→ checks Group conflicts
→ imports real targets
→ generates source-v1 and ast-v1 evidence
→ writes final YAML
```

The final YAML lists all selected Groups, but target, Replacement, aliases, and
dependency semantics remain in the matching Catalog version.

### Validate versus check

```bash
python -m das_driving.cli plan validate plans/customer.yaml
```

This validates YAML schema, external Catalog import, and inherited Plan
resolution. It does not inspect the model repository or target source.

```bash
python -m das_driving.cli plan check plans/customer.yaml \
  --repo /path/to/CustomerModel
```

This checks a generated final Plan against the repository and saved target
evidence. It does not produce a new file.

```python
resolved = das_driving.check(plan_path="plans/customer.yaml")
```

This resolves actual targets and Replacements and produces runtime decisions.
It does not install them. It may import modules and call a Wrapper factory once,
so Wrapper construction must not modify global state.

## 5. Runtime application

Apply before importing target model modules:

```python
import das_driving

report = das_driving.apply(
    plan_path="./plans/customer.yaml",
    report_dir="./dasdriving_reports",
)

from customer_model.train import main
main()
```

Run from the model repository when compatibility checks depend on the current
Git commit and dirty state. Call `apply()` once in each process.

Interpret decisions:

- `apply`: checks passed and the Group is eligible for execution.
- `skip`: disabled or not selected.
- `block`: a selected Group failed one or more checks.

A blocked Group and its dependents do not execute. Independent Groups continue.
An execution failure rolls back the whole Group; independent Groups continue
after successful rollback. Rollback failure is terminal.

## 6. Current limitations

- Plan target evidence covers the original target source/AST, not Replacement
  implementation or lower-level Kernel binaries.
- Source Hash and AST Hash are alternatives within `source.identity`; either can
  match.
- Project commit is an independent compatibility check. Matching target Hash
  does not currently cancel a commit mismatch.
- PatchReport covers checks and installation. It does not capture errors that
  occur later during training.
- Environment variables are not ModelPlan execution units. Keep them in
  `env.sh`, launch scripts, or deployment configuration until the current
  schema and launcher explicitly support them.
- `force_groups` can bypass only checks marked overrideable. Structural errors
  such as unresolved targets, alias conflicts, signatures, and declared
  conflicts remain blocked.

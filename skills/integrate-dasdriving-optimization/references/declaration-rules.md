# dasDriving declaration rules

## Contents

1. Minimal developer API
2. Replace versus wrap
3. Group boundaries
4. Dependencies
5. Targets and aliases
6. Public versus model optimization
7. Conflict handling
8. Implementation rules

## 1. Minimal developer API

Declare capabilities in a pure-Python Catalog:

```python
from das_driving import group, replace, wrap
```

Do not manually construct PatchSpec, PatchGroup, Registry, Handler, mechanism,
scope, SafetyLevel, or replacement factories for ordinary integration.

Example:

```python
ENCODER = group(
    "customer.encoder",
    replace(
        target="customer_model.encoder.Encoder.forward",
        replacement="customer_optimization.encoder.optimized_forward",
    ),
)
```

Importing the Catalog registers capabilities. It does not select them for
execution; ModelPlan performs selection.

## 2. Replace versus wrap

Use `replace` when the declared Replacement is the final installed object:

```python
replace(
    target="customer_model.encoder.Encoder.forward",
    replacement="customer_optimization.encoder.optimized_forward",
)
```

Use `wrap` when the declared function receives `(original, group_options)` and
returns the final object:

```python
def compile_wrapper(original, _options):
    compiled = torch.compile(original)

    @functools.wraps(original)
    def wrapped(*args, **kwargs):
        return compiled(*args, **kwargs)

    return wrapped
```

```python
wrap(
    target="customer_model.encoder.Encoder.forward",
    replacement="customer_optimization.compile.compile_wrapper",
)
```

Use `replace` for adapting a lower-level kernel whose parameter list differs.
Preserve the caller-facing signature in the Replacement and translate
arguments internally.

## 3. Group boundaries

Define a Group by functional atomicity:

> If any member is absent or rolled back, is the optimization still correct and
> complete?

If no, keep those members in one Group. If yes, split them so users can enable,
disable, check, and roll them back independently.

Do not group changes because they were developed in the same commit or improve
the same benchmark.

The Executor snapshots every member before the first modification. If a member
fails, it restores the complete Group in reverse order.

## 4. Dependencies

Declare only correctness dependencies:

```python
MODEL = group(
    "customer.encoder",
    replace(...),
    depends_on=("customer.backend",),
)
```

Use `depends_on` only when `customer.encoder` would be incorrect without
`customer.backend`.

Do not use it for:

- preferred ordering without correctness impact;
- indicating development history;
- expressing that two optimizations improve the same path;
- forcing all selected Groups to fail together.

Generator adds the dependency closure to the final Plan. Planner uses the same
Catalog relationship for execution order. A failed dependency blocks only its
downstream Groups.

## 5. Targets and aliases

`target` and `replacement` are importable Python object paths, not filesystem
paths.

Use `aliases` only for known references that imported or re-exported the same
original object:

```python
replace(
    target="mmcv.ops.modulated_deform_conv.modulated_deform_conv2d",
    aliases=("mmcv.ops.modulated_deform_conv2d",),
    replacement="customer_optimization.mdc.modulated_deform_conv2d",
)
```

The framework verifies alias identity and replaces/restores target and aliases
together. It does not scan all loaded modules to guess aliases.

Call `apply()` before importing the model project to reduce stale references.

## 6. Public versus model optimization

Use the current acceptance boundary:

### Public backend operator

Accept as public only when all apply:

- target is a stable backend/operator entry such as `mmcv.ops.*`;
- implementation does not import a model project;
- behavior does not depend on a model Forward, private data flow, or training
  configuration;
- the operator can be tested independently for supported inputs and gradients;
- the Group can be enabled and rolled back independently.

Function, class, Pack class, aliases, and framework registration entries needed
to provide one operator can belong to the same public Group.

### Model optimization

Keep as model-specific when it includes:

- model Forward rewrites;
- data preprocessing or prefetch;
- tensor-layout changes across model layers;
- model hotspot compilation;
- model-specific Autograd adapters;
- training entry or configuration changes.

Example decomposition:

```text
mmcv.mdc
├── MMCV MDC function
├── MMCV MDC class
├── MMCV Pack class
└── DCNv2 registration

bevformer.backbone
└── extract_img_feat channels-last and compile behavior
```

Do not call a Group public merely because its lowest-level call uses a common
kernel.

## 7. Conflict handling

Generator and Planner compare declared target and alias effects.

- Same Group, same entry: fix the Catalog; do not register twice.
- Different Groups, same entry and same Replacement: keep one Group.
- Different Groups, same entry and different Replacements: select one or
  refactor the boundary.
- Model Replacement still calls a stable lower-level entry: public and model
  Groups can coexist.
- Model Replacement inlines and removes the lower-level entry: target comparison
  cannot detect semantic containment; resolve during code review.

Never rely on last-wins registration or execution order.

## 8. Implementation rules

- Preserve positional and keyword argument behavior.
- Preserve outputs, Tensor shapes, dtype, device, and required gradients.
- Preserve decorators and metadata when external tooling depends on them.
- Use `functools.wraps(original)` for callable wrappers.
- Keep Wrapper construction free of irreversible side effects because runtime
  `check()` constructs it.
- Raise clear errors for unsupported configurations.
- Do not implement silent runtime fallback.
- Do not hide the original exception chain with `raise ... from None`.
- Keep complex Replacement logic in named functions so tracebacks identify the
  external optimization package or dasDriving component.

---
name: write-professional-docs
description: Write, restructure, and review professional Chinese or English product and technical documentation, including repository READMEs, documentation centers, installation guides, quick starts, user guides, developer guides, architecture documents, model integration guides, release notes, and public-facing open-source docs. Use when documentation must be concise, audience-appropriate, grounded in current code and real repository examples, free of discussion history, explicit about delivered capabilities and boundaries, visually readable after rendering, and validated before publication.
---

# Write Professional Documentation

Produce publication-ready documentation from verified facts. Treat documentation as a product interface, not as a record of the drafting discussion.

## Establish scope and audience

1. Identify the document type and primary reader before editing.
2. Read the existing document, linked documents, relevant source code, CLI help, configuration files, and tests.
3. Separate current behavior from plans, proposals, and historical designs.
4. Preserve user changes outside the requested documentation scope.

Use these boundaries:

- Root README: product positioning, application scenarios, supported scope, shortest usable path, and navigation.
- User guide: prerequisites, operations, expected results, and troubleshooting.
- Model guide: verified baseline, data and weight prerequisites, integration point, commands, results, and limitations.
- Developer guide: extension workflow, contracts, examples, tests, and acceptance criteria.
- Design document: architecture, responsibilities, state transitions, constraints, and rationale.
- Reference: complete fields, commands, parameters, return values, and error behavior.

Do not place internal architecture details on a product landing page unless users must understand them to complete a task.

## Ground every claim

- Verify APIs, command names, arguments, defaults, paths, configuration fields, status values, and exceptions against current code.
- Preserve exact code identifiers in backticks when a document refers to an API, configuration field, status, class, or file. Add a Chinese explanation separately instead of inventing a replacement term that no longer maps to the code.
- Make report wording, status descriptions, and configuration explanations correspond directly to the current data model and execution behavior.
- Run `--help`, schema validation, link checks, or focused tests when available.
- Prefer primary and authoritative sources for external facts. Add a direct link at the first relevant mention.
- Do not infer support from code presence alone. Distinguish implemented, tested, validated, supported, experimental, and planned.
- Do not describe a proposal, template, empty configuration, or unverified path as a delivered capability.
- State the exact boundary of failure handling, rollback, fallback, compatibility, and runtime behavior.
- Record unknown release facts as explicit release blockers rather than inventing values.

## Write in a professional style

- Use concise, objective, declarative sentences.
- Lead with application scenarios and user problems before implementation details.
- Use stable terminology consistently. Define an unavoidable technical term at first use.
- Prefer concrete nouns and verbs over slogans, qualifiers, and abstract chains of concepts.
- Keep one sentence focused on one claim. Split sentences that combine scope, mechanism, result, and limitation.
- Use parallel grammar in headings, lists, and table rows.
- Use tables only for repeated-field comparisons; use diagrams only when they clarify relationships or sequence.
- Keep headings descriptive and navigable. Avoid excessive heading depth.

Remove drafting traces, including:

- conversation references such as “as discussed”, “our current idea”, or “you can understand this as”;
- process language such as “for now”, “we will look at this later”, “first make a version”, or “the current stage considers”;
- subjective fillers such as “obviously”, “simply”, “actually”, or “it should be fine”;
- unsupported promotional claims such as “zero-cost”, “fully automatic”, “extremely fast”, or “seamless”;
- rhetorical questions and second-person dialogue in formal reference material;
- internal task IDs, personal paths, private hosts, credentials, temporary logs, and review conversations.

Use “current” only when describing a versioned state that may change. State the version, support matrix, or source of truth when relevant.

## Write from the delivered state

- Write for a reader who knows only the released repository and has no access to design meetings, chat history, intermediate implementations, or discarded proposals.
- Describe what the product does, when it applies, how to use it, and what its boundaries are. Do not explain the final design by narrating how the team arrived there.
- Remove comparisons with deleted mechanisms, earlier directory structures, former field names, and abandoned alternatives unless the document is explicitly a migration or compatibility guide.
- Do not justify an existing capability by saying that another idea was too complex, unnecessary, deferred, or removed. State the final responsibility and behavior directly.
- Do not include editorial commentary such as “this section does not discuss”, “only this case is shown”, or “the following is retained for now” unless it communicates a user-visible support boundary.
- When history is operationally relevant, identify the affected version, the observable change, and the required user action. Omit history that has no effect on the reader.
- Prefer the structure “object — behavior — condition/result” over conversational explanation, rhetorical setup, or conclusions that depend on preceding discussion.

## Separate scenario, capability, and assurance

Do not mix these categories:

- Application scenario: the situation in which a user needs the product.
- User problem: the obstacle the user needs resolved.
- Product capability: what the product provides to resolve it.
- Internal assurance: how the product validates, isolates, restores, or records its own actions.

Do not present an internal engineering concern as a user application scenario. Place checks, transactions, rollback, and reporting under reliability, behavior, or design unless they are directly required for user operation.

## State product boundaries

- State what the component owns and what remains the responsibility of the environment, upstream project, image, launcher, or user.
- Avoid absolute claims such as “does not modify source code” when integration still requires an entry-point change.
- Distinguish installation-time, initialization-time, and training-runtime behavior.
- Distinguish applying an optimization successfully from proving model correctness or performance.
- Describe unsupported configurations explicitly. Do not imply fallback unless code implements and tests it.

## Write executable examples

- Make commands copyable and complete within their stated prerequisites.
- Explain placeholders and the directory from which a command runs.
- Use public, relative, or parameterized paths. Exclude personal directories and internal network addresses.
- Show imports and definitions required by a code snippet; do not leave unexplained names such as `main()`.
- Search current implementations, declarations, configurations, and tests before inventing an example.
- Prefer the smallest stable example already delivered in the repository. Preserve its actual object paths, API names, casing, and behavior.
- Label shortened code as an excerpt and omit only details unrelated to the concept being explained.
- Use a synthetic example only when no suitable repository example exists. Label it as an API example and do not imply that it is used by a supported model.
- Keep genuinely generic examples generic. Put model-specific commands and environment variables in the model guide.
- Treat tests as evidence for API semantics and edge cases, but do not present a test-only path as a model-validated capability.
- Validate every documented CLI command against current `--help` output.
- Clarify whether a command validates syntax, inspects an environment, generates an artifact, modifies state, or starts training.

## Design for rendered output

- Inspect the rendered document on its target surface when layout matters; reviewing raw Markdown alone is insufficient.
- Use tables only when every column remains readable at the expected content width.
- Keep code lines reasonably short and split long Python strings or commands when this avoids horizontal scrolling.
- Avoid HTML or CSS width workarounds unless the publication platform explicitly supports and requires them.
- Visually verify headings, tables, code blocks, links, images, line wrapping, and spacing after substantive edits.

## Present performance and accuracy evidence

- Record hardware, device count, batch size, software versions, model commit, dataset, weights, command, warmup, sample interval, and statistic.
- Compare results only when measurement conditions are equivalent; otherwise label them as references rather than speedups.
- Separate measured values, calculated values, vendor data, official model data, and estimates.
- State units in table headers and define calculation formulas.
- Do not generalize one model, one commit, or one machine result to unsupported environments.

## Maintain the documentation system

- Keep one authoritative location for each fact; link to it rather than duplicating it.
- Keep root navigation short and role-oriented.
- Update support lists, model guides, references, and links together when a supported model or command changes.
- Use repository-relative links for repository files.
- Keep historical materials outside published documentation unless rewritten against current code.
- Name documents for the reader's task or concept, not as a list of implementation symbols. Use stable English filenames and clear audience-facing titles.
- When renaming or moving a document, update indexes and every inbound link, search for the old path, and run the repository documentation checker.

## Review before delivery

Perform this sequence:

1. Re-read the result as a first-time user without conversation context.
2. Remove statements that require hidden project history to understand.
3. Verify terminology, product scope, and support status.
4. Verify commands, paths, links, anchors, code fences, images, tables, and the final rendered layout.
5. Run repository documentation checks and `git diff --check` when available.
6. Review the diff for unrelated edits and duplicated facts.
7. Report changed files, validations performed, and unresolved publication blockers.

Do not claim publication readiness when license, support matrix, reproducible commands, security contact, or required validation evidence is missing.

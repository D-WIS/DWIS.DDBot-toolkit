---
name: model-dwis-config
description: Turn drilling-signal descriptions into intent sketches and generate, modify, validate, or repair ontology-grounded DWIS CONFIG files through either interactive clarification or non-interactive one-shot and batch processing. Use for DWIS signal modelling, existing CONFIG review, or questions that require resolving DWIS classes, predicates, graph constraints, and modelling patterns.
---

# Model DWIS Config

Produce a validated DWIS CONFIG through this workflow:

```text
collect or extract user inputs
  → summarize the intent sketch and confirm it when interactive
  → generate a DWIS CONFIG draft
  → validate and repair the draft
  → annotate the validated CONFIG with the intent sketch
  → deliver the final DWIS CONFIG
  → offer optional manifest conversion in the same response (interactive only)
```

Keep conversation, decisions, and file edits in the calling agent. Use DDBot Toolkit for ontology
grounding, example retrieval, and validation. Treat RDF as an internal derived representation, not
the deliverable.

## Operating modes

Select the mode once before starting:

- Use `interactive` by default.
- Use `non-interactive` only when the calling prompt or an appended system instruction explicitly
  requests non-interactive, one-shot, headless, or batch processing.

In non-interactive mode, do not ask questions, request confirmation, offer choices, or pause for
user input. Extract the strongest supported intent sketch from the supplied description and proceed
through generation, validation, repair, annotation, and delivery without interruption.

Prefer the smallest interpretation supported by the input, ontology, and retrieved examples. Omit
unsupported optional structure. When a choice is required to complete a valid CONFIG, choose the
best-supported conservative interpretation and record it in `assumptions`. Keep other absent details
in `missing_information`. Never stop solely to request clarification in non-interactive mode.

## 0. Resolve paths and check the runtime environment

Treat the working directory supplied by the host as `<cwd>` and as the complete filesystem
boundary. Read, search, glob, execute project files, and write only canonical paths contained within
`<cwd>`. Never access a parent directory, the filesystem root, a home directory, or a sibling
repository. Do not use input data, CONFIG files, examples, ontology files, caches, or output paths
from outside `<cwd>`. If any required input or requested output resolves outside `<cwd>`, report the
boundary violation and stop. Do not access it or look for an in-bound replacement.

Derive paths only from the selected Skill loader result:

1. Read the already-loaded `SKILL.md` canonical path from loader metadata, such as
   `details.resolvedPath` returned by `read(skill://model-dwis-config)`, and set it as
   `<loaded-skill-path>`.
2. Set `<skill-root>` to the parent directory of that exact `SKILL.md` path.
3. Set `<script-path>` to `<skill-root>/scripts/ddbot.py`.
4. Set `<ontology-path>` to `<skill-root>/assets/DWISVocabulary.ttl`.
5. Set `<example-corpus-path>` to `<skill-root>/assets/dwis-config-examples.jsonl`.

Before accessing sibling resources, confirm that `<loaded-skill-path>`, `<skill-root>`,
`<script-path>`, `<ontology-path>`, and `<example-corpus-path>` all resolve within `<cwd>`. Also
confirm that every requested CONFIG input and output path resolves within `<cwd>`.

Do not rediscover the Skill by name or guess an installation directory such as `.agents/`,
`.claude/`, or `.codex/`. Never run `find`, `locate`, `rg --files`, directory traversal, or any
filesystem-wide search to locate `SKILL.md`, the Skill root, the CLI, the ontology, or the example
corpus. If loaded-path metadata is unavailable, report that it is unavailable and stop; do not fall
back to searching. If a derived resource is absent, report that exact missing path and stop; do not
search for a replacement.

After resolving and checking the paths, read
[the environment guide](references/environment.md) and run its preflight once per session before
starting CLI-dependent work. Confirm that the sandbox can execute `uv`, use Python 3.11 or newer,
read the bundled ontology and example corpus, and write both its environment/cache and the requested
output location.

Do not repeat path resolution or the preflight after it succeeds. If it fails, report the exact
path or capability that failed and follow the guide's recovery path. Never claim that ontology
grounding, retrieval, or validation ran when the sandbox could not execute it. The toolkit is
offline after its Python environment is available, but the first `uv` invocation may require
network access to obtain Python or dependencies.

## 1. Collect user inputs

Read [the intent checklist](references/intent_checklist.md) before eliciting or interpreting a signal
description.

In interactive mode, build the description over as many dialogue turns as needed:

- Preserve facts the user already supplied; never ask for them again.
- Ask only questions whose answers can change the graph, ontology type, or required relation.
- Ask one small, coherent group of questions per turn. Use plain engineering language, not ontology
  identifiers.
- Prioritize the signal's meaning, value role, origin, and relevant context. Apply conditional parts
  of the checklist only when the signal needs them.
- Update the working intent after every answer. Briefly reflect the new understanding when useful.
- Record an explicit assumption only when it is safe and the user accepts it. Keep unresolved
  structural choices as clarification requirements.

For an existing CONFIG, initialize the working intent from the file and ask only about the requested
change or ambiguous existing semantics.

In non-interactive mode, perform no elicitation. Extract facts from the supplied description once,
mark absent optional details as `missing_information`, and resolve only indispensable choices using
the conservative assumption rule above.

## 2. Summarize and confirm the intent sketch

Convert the completed user input into the structure defined in the intent checklist. Keep the
user's terminology and distinguish:

- stated facts;
- accepted assumptions;
- information that is not applicable;
- unresolved clarification requirements.

In interactive mode, present the concise intent sketch to the user for confirmation before
generation. If the user has already confirmed the same structured intent in the current turn, do
not ask again. Do not proceed while a clarification requirement would materially change the
configuration.

In non-interactive mode, do not present the sketch for confirmation. Record any required conservative
assumptions and continue immediately with the extracted sketch.

## 3. Generate a DWIS CONFIG draft

Use the intent sketch—not the raw conversation—as the generation input.

1. Reuse the paths already derived from loader metadata; do not resolve or search for them again.
2. Ground uncertain domain terms with ontology search:

   ```bash
   uv run <script-path> --ontology <ontology-path> \
     ontology "standpipe pressure" --limit 10
   uv run <script-path> --ontology <ontology-path> \
     ontology "physical location" --kind property
   ```

3. Extract a compact keyword query from the intent sketch. Start with three to six discriminative
   terms covering the core concept, value role, origin, and location or equipment. Omit unknown and
   generic terms. Search optional concerns such as transformation or uncertainty separately when
   one query would mix unrelated patterns.
4. Search the shared example corpus before composing the CONFIG:

   ```bash
   uv run <script-path> examples \
     "standpipe pressure measured sensor" \
     --corpus <example-corpus-path> \
     --limit 5
   ```

   If results are empty or semantically weak, refine the keywords with ontology names, synonyms, or
   a more specific location/origin term and search again. Run a second focused search such as
   `"Gaussian uncertainty pressure measurement"` when the intent contains an additional modelling
   concern. Follow
   [the corpus guide](references/example-corpus.md).

5. Review the best matching examples before generation. Compare their `descriptions`,
   `intent_sketch`, and asserted `dwis_config`; identify only the entities and relations relevant to
   the confirmed intent sketch.

   Treat examples as modelling patterns, not as proof that every identifier still matches the
   loaded ontology. Resolve every copied class, object property, datatype property, and class
   shorthand against the current ontology. In particular, class shorthand objects must use an
   exact ontology class name; do not assume that the validator will append `Quantity` or expand an
   older alias.

   Inspect the JSONL directly only for a required field that the CLI output does not expose. Never
   load the complete corpus into context.

6. Compose the smallest configuration that expresses the sketch. Follow
   [the DWIS CONFIG format](references/dwis-config-format.md). Preserve valid identifiers when
   modifying an existing file. Save this candidate as the DWIS CONFIG draft. Do not present the
   draft as a completed DWIS CONFIG.

   When a top-ranked example's complete `dwis_config` covers all entities in the confirmed intent
   sketch, the draft MUST derive its relations from that example. Do not add relations that the
   example does not contain, even when they seem logically implied by the user's description. If
   the example lacks a relation the intent sketch requires, ask the user in interactive mode. In
   non-interactive mode, use the smallest ontology-grounded construction supported by the retrieved
   corpus and record any indispensable choice as an assumption.

   Preserve the instance identifiers from the matching example when their semantics align with
   the confirmed intent sketch. Only rename an identifier when the intent sketch requires a
   different instance (e.g., a new signal or entity that the example does not model).

## 4. Validate and repair the draft

Treat validation and repair as a separate gate between the draft and the final DWIS CONFIG.

1. Validate the draft:

   ```bash
   uv run <script-path> --ontology <ontology-path> validate <config-path>
   ```

2. Review `hard_errors`, `repair_suggestions`, `soft_comments`, and failed entries in `checks`.
   Trace each finding to the draft and the confirmed intent sketch. The checks include construction
   syntax and vocabulary, relation and attribute domain/range compatibility, graph connectivity,
   disjoint types, and functional-property conflicts.
3. Repair every hard error with the smallest change that preserves the confirmed intent. Do not add
   entities or relations merely to silence the validator.
4. Revalidate after every material repair. Repeat the validate → inspect → repair cycle until no
   hard errors remain.
5. If a repair requires an engineering choice not represented in the confirmed intent sketch, stop.
   Ask the user and reconfirm the sketch in interactive mode. In non-interactive mode, apply the
   smallest ontology-grounded repair, record the choice as an assumption, and continue validation.
6. Promote the draft to the final DWIS CONFIG only when the validation result reports `valid: true`.
   Keep remaining soft comments and accepted assumptions for the final summary.

7. Annotate the validated CONFIG with the confirmed intent sketch. Insert `# intent` comment
   lines **directly before the declarations or relations they describe**. Group related
   annotations together above the lines they qualify. Follow the format defined in
   [the DWIS CONFIG format](references/dwis-config-format.md).

   The annotation is part of the final deliverable and must be validated as part of the complete
   file. Revalidate after annotation to confirm the final file still reports `valid: true`.

## 5. Deliver the final DWIS CONFIG

Return the final CONFIG path, the annotated CONFIG content, a concise intent summary, and
hard-error and soft-comment counts. State any accepted assumptions that affect interpretation.
Never deliver an unvalidated draft, invent ontology terms, silently resolve a structural
ambiguity, copy an entire retrieved example, or claim that validation proves unstated engineering
intent.

In non-interactive mode, deliver the same final artifacts without asking follow-up questions. If a
runtime or validation failure makes completion impossible, report the failure directly rather than
requesting input.

Invoke the derived `<script-path>` rather than assuming that a global `ddbot` command or separately
installed Python package exists.

## 6. Offer optional manifest conversion

In interactive mode, after returning the final CONFIG, ask in the **same message** whether the user
wants to convert it to a manifest, for example: "Do you need to convert this DWIS CONFIG to manifest JSON? If so, reply 'Yes, convert it; company: [company name]; provider: [provider name]'."
Keep this question in the response text; do not insert it or any manifest content into the CONFIG
file. Do not run the converter or create a manifest unless the user explicitly requests conversion.
If conversion was already explicitly requested, proceed without asking for the same permission again.

In non-interactive mode, omit the follow-up question and generate a manifest only when the calling
prompt explicitly requests it.

When conversion is requested:

1. Reuse the final validated, annotated CONFIG as input without modifying it. Obtain the required
   provider and company names from the user or existing context; do not invent them. In
   non-interactive mode, report missing required metadata without blocking CONFIG delivery.
2. Derive `<manifest-script-path>` as `<skill-root>/scripts/manifest-creation/manifest_creation.py`.
   Reuse `<ontology-path>` as the vocabulary source; there is no separate JSON vocabulary. Confirm
   the script, ontology, input, and separate JSON output resolve within `<cwd>` using the existing
   path-boundary rules. The converter uses `rdflib`, already required by the toolkit, and its inline
   metadata declares that dependency. Keep using the preflight-selected `UV_CACHE_DIR`.
3. Pass the final CONFIG directly to the converter; the input extension is unrestricted, including
   `.dwis`. Run with an explicit ontology and an output path distinct from the CONFIG and ontology:

   ```bash
   uv run <manifest-script-path> --ontology <ontology-path> --input <config-path> \
     --provider "<provider>" --company "<company>" --output <manifest-json-path>
   ```

4. Return the manifest JSON path on success. If conversion fails, report the error and preserve the
   validated CONFIG; do not change its semantics merely to satisfy the converter.

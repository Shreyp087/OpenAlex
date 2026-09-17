# Engineering notes

Repair Desk asks a narrow question: can one data-quality report become an evidence-backed, repeatable engineering case?

It is an independent local prototype for an application to OpenAlex. It is not affiliated with OpenAlex, not a production data cleaner, and not a claim that OpenAlex lacks a curation workflow. OpenAlex already describes agent-assisted verification and correction in its [fixing-errors documentation](https://help.openalex.org/access/fixing-errors/). This artifact explores the regression-test handoff around that workflow.

## The boundary of the demonstration

The seed is a public OpenAlex snapshot of work `W4410234973`, a paper co-authored by Shrey Patel. All demonstrated faults and support tickets are synthetic. The fetched record is evidence of its fetched state; it is not proof of an OpenAlex defect. No private support queue was accessed, and nothing is written to OpenAlex.

The cases deliberately require different outcomes:

| Case | Judgment being exercised |
| --- | --- |
| Affiliation drop | Diagnose local information loss against preserved input. |
| ORCID conflict | Escalate an identity conflict rather than infer a merge from a name. |
| Sparse metadata | Treat missing evidence as a limit, not a license to invent a repair. |
| DOI replay | Preserve stable work identity across repeat deliveries and DOI spellings. |

## Local architecture

The implementation uses Python 3.9+ and SQLite from the standard library. Its bronze/silver/gold language is a conceptual correspondence to the role, not a Databricks deployment.

- **Bronze:** delivered payload bytes are stored with a SHA-256 key. SQLite triggers reject updates and deletion. This preserves the local input needed to reproduce a decision.
- **Silver:** a work is materialized by OpenAlex work ID. A normalized representation and content hash support repeatable processing; DOI alone is not used as the work's primary identity. A foreign key points back to the source payload.
- **Gold / case output:** replay results and findings expose the scenario, evidence, decision, and checks. They are deterministic fixture results, not learned author or institution predictions.
- **API and casebook:** the local Python service exposes the demonstration; a static casebook can show precomputed outputs. There is no external model call, hosted search cluster, worker deployment, or credentials requirement for the bundled demo.

Preserving source text and normalizing identifiers are different operations. In particular, raw affiliation text must remain intact. OpenAlex's `authorships[].affiliations` mapping carries the relationship between each original string and the institution IDs it produced; flattening those IDs loses that relationship. See the [raw affiliation reference](https://help.openalex.org/data/raw-affiliation-strings/).

## Decision policy

The local artifact should be able to show a repair, escalate for review, or decline to change anything. Each path needs visible evidence. Absence of a field is not proof of a transform bug. A conflicting identifier does not become safe just because a name matches. A case is only a confirmed local regression when the fixture's known input and transformation demonstrate the violation.

An affected-record count in this artifact describes the local fixture only. It must not be extrapolated to the OpenAlex corpus. Real affiliation curation operates on exact strings and can affect multiple works, so any live deployment would need an independently measured impact set and the existing permission model. See the [AI curation guide](https://help.openalex.org/access/fixing-errors/ai-curation-guide/).

## What the tests establish

The suite checks explicit invariants and adversarial cases in a tiny constructed dataset. It can demonstrate that a known injected loss is detected, an identity conflict is gated, a negative control remains unchanged, and repeated delivery preserves local materialization behavior.

It does **not** measure precision or recall on the production corpus, establish a general author-disambiguation model, prove throughput at scale, or validate all source formats. Fixture pass rates are development checks, not estimates of real-world accuracy. Source freshness and upstream correctness remain separate questions.

The next evaluation should use reviewed historical cases plus difficult non-errors. Separate cases used to author rules from a held-out set. Report incorrect changes, missed issues, abstentions, reviewer agreement, and operational cost by failure type. A high aggregate pass rate can conceal a harmful false repair.

## A credible route to a larger pipeline

This is a proposed extension, not implemented functionality.

1. **Start from the existing jobs.** Trace one agreed failure through actual ingestion, matching, serving, and support. The public [institution-matching jobs](https://github.com/ourresearch/openalex-databricks/tree/main/jobs/string_matching_institutions) and [author-disambiguation pipeline](https://github.com/ourresearch/openalex-databricks/tree/main/jobs/author_name_disambiguation/v3) provide context; integration requires the team's actual contracts and operating knowledge.
2. **Preserve replay identity.** In a Delta-backed design, retain source ID, ingest batch, source version, exact payload hash, and transform version. Give repeated events stable keys. A SQL `MERGE` needs explicit tie-breaking and late-arrival semantics; the command alone does not guarantee idempotency.
3. **Scope incremental work.** Process changed source partitions or an agreed change feed, then join to affected work IDs. Keep raw evidence addressable. Partition and clustering choices should follow measured volume and query patterns, not this demo's tiny SQLite schema.
4. **Compare before publishing.** Run the candidate transform against a bounded reviewed slice. Materialize a proposed diff and an exact impact set. Preserve previous values and the transform version for rollback. Do not advance a replay to serving merely because its job completed.
5. **Roll out in stages.** Shadow first, then a small approved slice, then expand only when reviewed cases and non-error controls remain sound. Track decision classes and source-specific drift. Reconcile the served API after its documented update delay.
6. **Return to the user.** Reply with the record, evidence, outcome, and remaining uncertainty. Link the internal case to its regression and owner. When a new ticket contradicts the rule, add a counterexample rather than quietly broadening the claim.

## AI assistance and ownership

This artifact was generated with AI assistance for Shrey's application. It should be reviewed and run by the applicant before submission. The candidate should be able to explain the evidence gates, inspect every meaningful change, describe what the tests do not establish, and choose the next evaluation. No claim of unassisted implementation is made.

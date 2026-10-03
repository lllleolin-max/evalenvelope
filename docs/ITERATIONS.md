# Correction evidence

The initial complete build is followed by real adversarial review, retained failing probes and code corrections. Exact before/after commits and ordinary-wheel observations will be recorded here after those reviews. No score is self-assigned. Build/harness fixes are separate from substantive rounds.

Initial complete implementation: `2c6be20`. An actual contrast assertion failed because the cheapest-first baseline spent budget on zero-width scores. Harness-only correction `1d956aa` deferred zero-benefit actions except for coverage; [original failure](evidence/harness-before.txt) is retained and this does not count as a substantive round.

## Round 1: foreign state accepted by direct SDK calls

Before: `1d956aa2ef5974a3a37169fcd74cc9aa51cea92e`. [Unchanged probe](evidence/probe_round1.py) found `envelope`, `plan` and `import_observations` accepted a State belonging to another immutable model identity. The CLI parser had checked it, but the public SDK boundary had not. [Actual before failure](evidence/round1-before.txt) contains all three accepted operations.

Correction: shared `require_state` binds state identity and manifest digest and revalidates canonical actual observations at every analysis/import/check boundary. Added regression test covers the independent checker as well. The after commit is this section's introducing commit, a direct child of the before SHA; the next evidence entry records its full SHA and fresh ordinary-wheel result.

Reproduce before/after: `python tools/verify_install.py --ref COMMIT --probe docs/evidence/probe_round1.py`. The unchanged probe is run against the package installed from that exact Git archive, after the principal tests/CLI demo/contrast pass.

Round 1 after: `5da6e622c012055b56c12708033baf16ae676486`; [ordinary-wheel after output](evidence/round1-after.txt) records PASS for all three SDK operations, Git/archive/wheel/install module hashes, CLI workflow and independent-oracle suite.

## Round 2: lossy JSON identity/version parsing

Before: `5da6e622c012055b56c12708033baf16ae676486`. [Unchanged probe](evidence/probe_round2.py) found that `version:true` was accepted as integer 1 by manifest parsing and certificate checking, and a registered CLI invocation accepted a manifest with contradictory duplicate `version` keys (exit 0). [Actual before failure](evidence/round2-before.txt) is retained.

Correction: exact integer version validation at all schema boundaries; CLI JSON object-pair decoding refuses duplicate keys and nonfinite JSON constants before any identity/cost parsing. This prevents silently discarding a conflicting declared field. Added regression tests. The after commit introducing this section is a direct child of the before SHA; after output and full SHA are recorded in the next entry. Reproduce with `python tools/verify_install.py --ref COMMIT --probe docs/evidence/probe_round2.py`.

Round 2 after: `369f667916faa44a92c92ae9d93671f8aba3c908`; [ordinary-wheel output](evidence/round2-after.txt) records rejection of all three original failures and passing principal suite/demo/contrast.

## Round 3: idempotent replay failed at the state resource boundary

Before: `369f667916faa44a92c92ae9d93671f8aba3c908`. [Unchanged probe](evidence/probe_round3.py) fills the supported 500 paired-item manifest with 1000 actual score records, then retries one record and the entire export. Both legitimate idempotent replays raised the raw 1000-row cap even though unique stored records stayed at 1000. [Actual before output](evidence/round3-before.txt) preserves both errors and the separate conflicting-replay rejection.

Correction: bound state and incoming exports separately, allow only their bounded internal concatenation, then apply the 1000 unique-event stored-state cap after event conflict detection and deduplication. New confirmation event IDs beyond the cap still refuse; conflicting payloads still refuse. Added full-capacity regression tests. The section's introducing code commit is a direct child of the before SHA; the next entry records its full SHA and after output. Reproduce with `python tools/verify_install.py --ref COMMIT --probe docs/evidence/probe_round3.py`.

Core correction commit: `2da6216`. Its archive installed successfully, but the post-change suite exposed a misplaced test assertion (`NameError: bad`), introduced while adding the regression test. [Actual harness failure](evidence/round3-harness-failure.txt) is retained. The next test-only commit moves the existing out-of-range assertion back into its original test. This additional harness repair is not a substantive round and does not silently inherit a passing result at `2da6216`; later evidence names the repaired commit explicitly.

Round 3 validated after the test-only repair at `ac0fbae99f32af418b7b1fc8258490bd070cf335`; [fresh ordinary-wheel output](evidence/round3-after.txt) records both unchanged replay probes PASS and retained conflicting-replay rejection. Because this round required a separate harness repair before the complete suite passed, the project also performs Round 4 as a third uninterrupted direct-parent substantive FAIL → correction → PASS cycle in addition to Rounds 1 and 2.

## Round 4: independent checker accepted false bounded-search metadata

Before: `ac0fbae99f32af418b7b1fc8258490bd070cf335`. [Unchanged probe](evidence/probe_round4.py) produced a legitimate node-limited UNKNOWN plan, then changed its reduction upper bound to -1, replaced its prior-only objective, claimed more visited nodes than its declared budget and set the budget to zero. Even the independent subset oracle accepted every corruption because it only checked feasible selections. [Actual before failure](evidence/round4-before.txt) preserves all four failures.

Correction: the checker now validates declared objective, positive node budget, observed node count, absence of fake incumbent fields, status-specific reduction bounds and their relation to the actual remaining uncertainty. It still distinguishes feasibility verification from exhaustive proof of OPTIMAL/INFEASIBLE; UNKNOWN stays UNKNOWN. Added corruption and no-incumbent regression tests. The after commit introducing this section is a direct child of the before SHA. Reproduce: `python tools/verify_install.py --ref COMMIT --probe docs/evidence/probe_round4.py`.

Round 4 after: `f3964a74ca7fc8bc663a87bb5483bf68e89b9232`; [ordinary-wheel output](evidence/round4-after.txt) records the four unchanged corruption probes refused, with the principal tests, CLI workflow and contrast passing.

## Round 5: malformed checker inputs leaked Python exceptions

Before: `f3964a74ca7fc8bc663a87bb5483bf68e89b9232`. [Unchanged probe](evidence/probe_round5.py) supplies list-valued action/witness IDs and a non-object JSON certificate through the registered CLI. SDK checkers leaked TypeError; CLI returned traceback/exit 1 instead of the documented input refusal/exit 2. [Actual before failure](evidence/round5-before.txt) is retained.

Correction: typed ID checks before dictionary membership, an explicit CLI certificate-object boundary, and typed refusals for overnested/invalid-UTF8 JSON. Added SDK regression tests. This section's introducing commit is the direct child of the before SHA. Reproduce with `python tools/verify_install.py --ref COMMIT --probe docs/evidence/probe_round5.py`.

Round 5 after: `dc772c9`; [ordinary-wheel output](evidence/round5-after.txt) records the unchanged malformed-ID and CLI probe PASS, with the complete principal suite/demo/contrast. No failure was removed. Final freeze validation also executes every retained probe from the archived source and records its SHA-256; it reports individual test names, archive/wheel hashes and exact source/install byte linkage.

## Commit relationships and claims

Gate-qualifying uninterrupted substantive pairs: `1d956aa → 5da6e62` (foreign SDK state), `5da6e62 → 369f667` (strict JSON/version), `ac0fbae → f3964a7` (bounded checker), `f3964a7 → dc772c9` (typed malformed refusals). Each arrow is a direct parent relationship and the same probe failed before and passed after in a fresh ordinary wheel. Round 3's substantive fix `369f667 → 2da6216` is retained with the explicit separate harness failure/repair; it is not needed to manufacture the three-round gate. Resolve abbreviated commits through local Git; after outputs contain full SHAs.

The checker verifies exact attainable endpoints and preservation of actual scores, and independently verifies prior action accounting, hard constraints and the conservative UNKNOWN upper bound. It validates node-budget **consistency**, not a replay of every search step. Its default `optimality:not_checked` does not certify OPTIMAL/INFEASIBLE; `--prove-optimal` uses independent exhaustive subset enumeration (≤20 actions) and verifies those claims including lexical ties. It never upgrades UNKNOWN. Source labels and plan hashes are local evidence, not authentication of observations or proof a caller never privately viewed scores.

Local validated interpreter: Windows Python 3.14.3. Only this Python is installed locally. The committed CI matrix actually performs the same ordinary-wheel checks on Ubuntu/Windows, Python 3.11/3.14 when publication triggers it; no remote run is claimed here. No customers, revenue, safety guarantee or independently accepted scores are claimed.

## Independent-review correction: legal derived results were uncheckable

Before: `7f4514563ebfd2dd614c5c4adee86937d4a0a3c7`. Fresh archive/normal-wheel execution of the unchanged external independent number probe (SHA-256 `4bc186cd03ba0946fcf7352a15278685a8f5e7925e283ab8cde069a8d40bd1c3`) reproduces product exit 1 with the correctly computed 213-character endpoint. [Before evidence](evidence/number-before.json) preserves the failure and all six Git/archive/wheel/site associations. The setup driver succeeds in recording that failure; its exit 0 is not a passing product result.

Correction: separate source literal limits from canonical derived-result encoding/checking; use bounded decimal chunks rather than global integer conversion settings; retain exact source-decimal persistence within its original cap. All endpoint/width/contribution/witness and plan cost/reduction/upper-bound numeric outputs follow the same derived protocol, while source ingress remains strict. Six additional meaningful numeric tests exercise larger legal results, 500 items, >4300-digit components, SDK/actual CLI, noncanonical/tampered/oversize/negative fields and process-setting invariance. [Mathematical bounds and retained precommit/setup failures](DERIVED_NUMBERS.md) document the scope.

This code correction's introducing commit is a direct child of the before SHA. The external probe is neither copied over nor edited; after evidence will name its exact application commit and final freeze. Documentation redaction is not a core iteration. Existing original correction history and genuine failures remain; this independent-review correction is an additional substantive cycle rather than a claim that old scores still apply.

After application: `609403b1c430ccec553da84723c1cbcd60f3afe9`, verified as a direct child of `7f4514563ebfd2dd614c5c4adee86937d4a0a3c7`. [Fresh exact-SHA after evidence](evidence/number-after.json) records 19 tests PASS, all six source/archive/wheel/site modules equal, actual target-sysconfig CLI/demo/contrast success and the unchanged `4bc186...` product probe exit **0**. The original probe's independently computed 213-character endpoint is accepted. This driver covers reproduction and package linkage; it does not complete the independent scoring review. The final evidence-only commit leaves this application's source/tests/tools unchanged and receives its own full-suite archive/wheel verification.

Additional verification of the file-reader boundary: [500-item maximum-literal CLI stress](evidence/filecap-after.json) uses 2000 pairwise-coprime denominators, confirms 250003-digit derived components and 1649167-byte file round trip with unchanged digit setting; a >4 MiB file refuses with exit 2. An added size-bound test computes complete envelope/plan JSON shape upper bounds of 3299563/2022656 bytes, including every generated field and row. This adds verification, not another core correction. Final tests increase to 20; library source remains identical to the direct application commit.

The later `23f6d1c48eaa379f0f581374dc5148553f30ff6b` numeric follow-up preserves the original reduced-fraction manifest/state hash commitments separately from source-decimal persistence. Independent SHA-256 expectations now check those identities, so the persistence repair does not change existing semantic commitments or receipt bindings. All 20 tests, original 5 probes and the unchanged external number probe passed from its fresh archive/wheel.

## Independent-review correction: receipt-cap output violated state closure

Before: `23f6d1c48eaa379f0f581374dc5148553f30ff6b`. The unchanged external receipt probe (SHA-256 `2bfa3bf4bcd6c9122ac2fd1e2199701fe9af14c79f6602a2341abb7976a2b65e`) parses 1000 supported synthetic local receipt declarations and imports an empty actual batch against a valid frozen empty plan. The product emitted 1001 receipts and its own `parse_state` refused the result. [Fresh exact-parent before evidence](evidence/receipt-before.json) records 20 tests PASS, the number probe PASS and receipt probe **exit 1**, with six Git/archive/wheel/site module associations.

Correction: check the existing hard receipt cap before appending a frozen-plan receipt and refuse with Error, preserving the prior state and CLI source/output files. The cap is not widened, history is not silently truncated or deduplicated, and unplanned empty/identical-event imports retain idempotency. Three substantive receipt tests cover exact 999→1000 success/round trip, 1000→typed refusal, stale plans, duplicate local declarations, conflicting actual event IDs, planned actual imports at the cap, and actual registered-CLI no-op/output-preservation behavior. This correction's introducing commit is a direct child of the before SHA. External probes/assets are unchanged; this is separate from the derived-number cycle and documentation redaction.

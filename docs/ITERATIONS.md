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

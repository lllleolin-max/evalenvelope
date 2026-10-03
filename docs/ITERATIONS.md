# Correction evidence

The initial complete build is followed by real adversarial review, retained failing probes and code corrections. Exact before/after commits and ordinary-wheel observations will be recorded here after those reviews. No score is self-assigned. Build/harness fixes are separate from substantive rounds.

Initial complete implementation: `2c6be20`. An actual contrast assertion failed because the cheapest-first baseline spent budget on zero-width scores. Harness-only correction `1d956aa` deferred zero-benefit actions except for coverage; [original failure](evidence/harness-before.txt) is retained and this does not count as a substantive round.

## Round 1: foreign state accepted by direct SDK calls

Before: `1d956aa2ef5974a3a37169fcd74cc9aa51cea92e`. [Unchanged probe](evidence/probe_round1.py) found `envelope`, `plan` and `import_observations` accepted a State belonging to another immutable model identity. The CLI parser had checked it, but the public SDK boundary had not. [Actual before failure](evidence/round1-before.txt) contains all three accepted operations.

Correction: shared `require_state` binds state identity and manifest digest and revalidates canonical actual observations at every analysis/import/check boundary. Added regression test covers the independent checker as well. The after commit is this section's introducing commit, a direct child of the before SHA; the next evidence entry records its full SHA and fresh ordinary-wheel result.

Reproduce before/after: `python tools/verify_install.py --ref COMMIT --probe docs/evidence/probe_round1.py`. The unchanged probe is run against the package installed from that exact Git archive, after the principal tests/CLI demo/contrast pass.

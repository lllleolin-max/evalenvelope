# Existing foundations and executable contrast

Primary sources browsed 2026-10-03 by the GPT-6.1-Sol / Ultra implementation agent:

- [UK AI Security Institute Inspect scoring metrics](https://inspect.aisi.org.uk/metrics.html) documents accuracy/means, standard errors, bootstrap uncertainty, confidence intervals, grouping and scorer APIs. Those are established evaluation foundations.
- [clavis-systems evalstats](https://github.com/clavis-systems/evalstats) describes paired significance-aware model evaluation, confidence intervals, paired randomization tests, multiple-comparison correction and ratings. Paired statistics are established work.

EvalEnvelope does not implement or improve those statistical procedures. It makes a different supported statement: deterministic attainable completions of a specific **finite** incomplete manifest with independent boxes, coupled to a prior-only frozen acquisition and actual-import workflow. The engineering combination is the candidate distinction; it is not a new mathematical endpoint formula or knapsack algorithm, a patent claim, a first-ever claim, or proof that the linked tools lack an undocumented feature. Neither Inspect nor evalstats is executed here; no compatibility or performance advantage over either is asserted.

`tools/contrast.py` executes a disclosed tiny baseline preferring the cheapest available actions in order, and an exact reduction planner. Both use the same items, boxes, costs, budget and completed-pair coverage. To avoid unfairly rejecting the baseline on hard constraints, it enumerates feasible subsets then prioritizes cheap-action inclusion; this is an intentionally small baseline, not an established package. No future values enter either.

Four falsifiable synthetic cases: a weighted high-value follow-up wins by 9/10 versus 1/10 width reduction; uniform weights/costs yield equal reduction; full coverage forces equal collection; insufficient coverage budget makes both infeasible. `tools/demo.py` demonstrates the distinct denominator/actual-import decision and an equal complete-data case. A completed-only statistic or bootstrap reuses the observed subset and cannot repair the changed target denominator; the runnable baseline is the completed-only mean, not a library bootstrap implementation.

The value claim is limited to those measured mechanisms. It does not establish population accuracy, sequential inference, universal optimizer superiority, production evaluation speedups, or market demand. Independent reviewers determine whether the demonstrated workflow clears the portfolio differentiation gate.

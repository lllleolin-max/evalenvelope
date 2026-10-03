# Security and supported trust boundary

This is a local untrusted-JSON analysis tool, not a scoring sandbox or release approver. Do not store secrets or sensitive raw prompts in IDs/source labels. The CLI does not execute commands from data or contact a model. Validate exporter provenance separately; SHA-256 commitments detect content mismatches but do not authenticate a judge, signer, time or author. An operator can lie about actual observations or privately inspect scores before planning; the tool cannot infer that from a file.

Resource caps bound declared structures and search nodes. Very large rational denominators can still cost CPU. Use process-level limits for hostile environments. Inputs with foreign identities, unknown fields, malformed ranges, conflicting observations, unsupported couplings or over-limit structures are refused. JSON output files atomically replace the requested local destination; choose that destination deliberately.

Report reproducible correctness/security issues through the repository's GitHub issue tracker after publication. Use a minimal synthetic fixture without private data. There is no monitored security email or promised response SLA. Deployments need their own protected review and observation-integrity process.

# Current-document path redaction

The seven historical failure logs in `docs/evidence/` were copied byte for byte to the separate local, unpublished backup directory `publication/private-local/evalenvelope` beside this repository before editing. Their original byte counts and SHA-256 hashes are recorded in that backup's `BACKUP_MANIFEST.json`. These backups are outside this repository and are not release artifacts.

Only machine-specific absolute repository/temp prefixes were replaced in the current documents: `<REPO>` means this repository checkout, and `<WHEEL_WORK>` means the isolated archive/wheel-install temporary directory. Relative filenames, stack line numbers, exception classes/messages, failing assertions, test counts, search defects and nonzero exit results remain as originally recorded. Existing encoding artifacts are retained. The logs still describe genuine failures; none was changed into a successful run.

The previous freeze is `cc32dceca04702a0a6793ed1e77c7c21ae433c58`. Library, tests, tools, probes, receipt hashes and package version 0.1.0 are unchanged by this documentation-only correction; `src`, `tests` and `tools` Git tree IDs match that commit exactly. This correction is not an additional implementation iteration.

Git history was not rewritten. Historical commits still contain the original machine paths, which are local path metadata rather than credentials. This document makes no claim that the entire Git history has been redacted. Original historical FAIL evidence and correction SHAs remain available for independent replay. A fresh installation review of the new documentation commit must record its new exact SHA, rather than treating previous archive/wheel hashes as identical artifacts.

中文：当前公开的七份失败日志只将本机绝对目录前缀替换为可移植标记，原始完整字节已先备份到仓库外的本地私有目录。失败断言、异常、行号、测试数及非零退出结果均保留。代码、测试、工具、探针和版本没有改动；此次不增加核心修正轮次。没有重写 Git 历史，旧提交仍含原本机路径，因此不声称“全历史脱敏”。

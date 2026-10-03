# EvalEnvelope

Decide what a partially scored **named finite paired benchmark** can establish, then freeze a cost/coverage-feasible collection plan before importing its actual results.

EvalEnvelope retains the original stratum sizes and target weights. It computes exact attainable completion bounds, emits both endpoint witnesses, and checks them independently. Its bounded search chooses missing old/new observations by worst-case interval width reduction, under acquisition costs, hard completed-pair coverage and pinned actions. A frozen plan is bound to the manifest/model/scorer and prior observation state.

This is a deterministic finite-manifest statement. It supplies no population confidence interval, unbiased adaptive-sampling guarantee, or production-release safety certification. Constructed witnesses are never observations.

## Install and run

Python 3.11+; standard-library runtime. Ordinary wheel installation:

```sh
python -m pip wheel --no-deps --wheel-dir dist .
python -m pip install dist/evalenvelope-0.1.0-py3-none-any.whl
evalenvelope --help
```

Generate and run the complete local synthetic workflow using the registered executable (on Windows use the Scripts directory returned by the installed interpreter's `sysconfig.get_path('scripts')`):

```sh
python tools/demo.py evalenvelope demo-output
python tools/contrast.py
python tools/verify_install.py --output .evidence/final.json
```

The demo calls the real CLI for manifest → empty state → actual prior-score export import → certificate/check → frozen plan/check → separately revealed actual synthetic scores → import → new certificate/check. Outputs are JSON files under the supplied directory. The four paired items have fixed quick/critical weights 1/5 and 4/5. Completed-only analysis initially sees +1 and would pass at margin zero; the correct interval is [-3/5, 1/5] and is inconclusive. Acquiring two critical new-model scores for declared cost 6 reveals zeros, yielding exactly -3/5 and FAIL. A complete-data fixed-weight baseline agrees.

Example commands on those generated files:

```sh
evalenvelope analyze --manifest demo-output/manifest.json --state demo-output/prior.json --margin 0
evalenvelope plan --manifest demo-output/manifest.json --state demo-output/prior.json --options demo-output/options.json --output plan.json
evalenvelope check --manifest demo-output/manifest.json --state demo-output/prior.json --certificate plan.json --prove-optimal
evalenvelope import --manifest demo-output/manifest.json --state demo-output/prior.json --observations demo-output/revealed-synthetic-observations.json --frozen-plan plan.json --output next-state.json
```

Importing new observations narrows width by the selected prior reduction. Their values can shift endpoints in either direction; width reduction does **not** promise a passing release decision. A legitimate user may import non-planned actual records without `--frozen-plan`; those imports do not produce a frozen-plan receipt.

## SDK

```python
from evalenvelope import parse_manifest, empty_state, envelope, plan, check_envelope
manifest = parse_manifest(manifest_json)
state = empty_state(manifest)
certificate = envelope(manifest, state, margin="1/100")
check_envelope(manifest, state, certificate)
next_plan = plan(manifest, state, {"budget": "20", "coverage": {"critical": 4}})
```

JSON exact numbers must be integers or decimal/rational strings; float JSON numbers are refused. See [format and mathematics](docs/MODEL.md), [commercial hypothesis](docs/USE_CASE.md), [comparison and boundaries](docs/COMPARISON.md), [correction history](docs/ITERATIONS.md), and [security](SECURITY.md).

## 中文说明

EvalEnvelope 面向评测负责人：当固定配对样本清单尚未全部评分时，判断所有合法缺失评分补全能否改变模型发布结论，并在看到未来分数之前冻结下一批采集计划。

它按原始分层大小计算固定权重，缺失分数保持区间，绝不补零或按已完成样本重分母。输出可达的精确上下界、完整极值补全见证和独立检查结果。采集计划按照“剩余区间宽度减少”优化，保留预算、必选项和各层完整配对覆盖要求；old/new 分别计费，只有显式声明的 bundle 才采用组合成本。

运行上面的安装与 `tools/demo.py` 命令即可得到完整 JSON 工作流。合成例子中，先完成的便宜样本显示改善 +1，但固定清单正确区间为 [-3/5, 1/5]，不能据此通过。冻结计划后导入另外两项真实执行的合成 fixture 分数，得到 -3/5 并拒绝；完整数据时与普通固定权重基线一致。

支持范围是有限、预先声明、独立评分箱约束。它不是总体置信区间，也不证明线上发布安全；见证是数学构造，不能冒充观测。客户、收入和付费意愿均未知；收费路径仅为评测系统集成和运行支持的待验证假设。独立评审可以否决项目，项目没有自评分数。

# SlateSignal Model Card

## Scope

SlateSignal forecasts worldwide theatrical gross for real films with US
theatrical release records. The public output is an interval, not a guarantee.
The system is intended for research, release-calendar exploration, and decision
support. It is not accounting truth, investment advice, a talent valuation
system, or an autonomous greenlight decision.

## Active Baseline: `bert-xgb-v1`

The active model preserves the original research implementation:

| Component | Contract |
| --- | --- |
| Text encoder | `bert-base-uncased` |
| Token limit | 512 |
| Pooling | attention-mask-aware mean |
| Text features | 768 |
| Structured features | 15 |
| Total features | 783 |
| Regressor | XGBoost |
| Target | `log1p(worldwide nominal USD)` |
| Training cutoff | 2023-12-31 |

Structured inputs are log budget, release decade, three director-history
features, and ten primary-genre indicators. Buzz is not multiplied into this
baseline. The UI displays unsupported production factors as context or
unavailable.

### Results

| Split | Films | MAE | log-MAE | R2 | 80% coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2024 untouched validation | 121 | $111.15M | 1.4375 | 0.1534 | 79.34% |
| 2025 closed holdout | 24 | $115.03M | 1.6216 | -0.0346 | 75.00% |

The 2025 records are retrospective evaluation locks. They are not represented
as predictions that were publicly issued before release.

The original presentation reported $141.21M MAE for structured XGBoost,
$128.99M for TF-IDF + XGBoost, and $115.03M with BERT + XGBoost. Those historical
figures remain versioned and are not substituted for the reconstructed splits.

## Released-Film Temporal Evaluations

The released-film explorer also includes four deterministic temporal folds.
Each fold trains only on earlier release years, selects its tree count and
80% split-conformal radius on the immediately preceding year, and then scores
the target year.

| Fold | Films | MAE | log-MAE | R2 | 80% coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2021 | 112 | $83.59M | 1.6671 | 0.1489 | 89.29% |
| 2022 | 121 | $106.41M | 1.6912 | 0.2034 | 84.30% |
| 2023 | 126 | $98.64M | 1.3665 | 0.1680 | 88.89% |
| 2024 | 121 | $112.21M | 1.4660 | 0.1369 | 82.64% |

These 480 runs were sealed after the fact with `is_ex_ante: false`. Temporal
target separation prevents target-year revenue reuse, but the research
metadata snapshot was assembled after release. They therefore support honest
predicted-versus-actual exploration, not a claim that every input was public
at the simulated January 1 cutoff.

## Corrected Candidate: `multimodal-xgb-v2`

The candidate adds time-frozen director, cast, and studio histories; CPI
normalization to 2025 dollars; release timing; runtime; certification;
franchise proxy; and explicit missingness. Hyperparameters were selected on an
internal 2022-2023 fold, then evaluated on untouched periods.

| Split | Baseline MAE | Candidate MAE | Baseline log-MAE | Candidate log-MAE |
| --- | ---: | ---: | ---: | ---: |
| 2024 validation | $111.15M | $104.22M | 1.4375 | 1.3422 |
| 2025 holdout | $115.03M | $112.40M | 1.6216 | 1.4285 |

The candidate is **not promoted**. Its 2025 80% interval coverage was 66.67%,
and the matched-cohort Wikidata fairness audit does not yet have sufficient
power. Better point estimates are not enough to pass the release gate.

## Corrected Research Defects

- Validation rows and embeddings are checksum-aligned.
- Serving uses the training-time mean pool, not CLS.
- Early stopping does not inspect the final holdout.
- Post-release social signals are excluded from pre-release backtests.
- Hand-authored social revenue multipliers are removed.
- Corrected targets are CPI-normalized before training.
- The original budget-confounded, name-derived binary gender analysis is rejected.
- An additional training structured-row and embedding-order misalignment is documented.

## Uncertainty

P10/P50/P90 are derived from absolute log residuals on the 2024 calibration
split and segmented by production budget when sample size permits. Missing
metadata never receives a fabricated source value. It either widens the
interpretation, is model-imputed with a label, or leaves a target unavailable.

The original baseline supports worldwide total only. Domestic opening,
domestic total, and international total remain null until source-complete
targets pass their own temporal evaluations.

## Fairness

Gender, race, ethnicity, age, disability, religion, sexual orientation, and
other protected attributes are excluded from predictive inputs.

Track-record variables can encode unequal historical access to budgets,
distribution, franchises, and opportunity. Fairness evaluation therefore uses
demographic annotations only after prediction, with matched budget, genre, and
year cohorts plus bootstrap confidence intervals. Small or incomplete groups
produce `insufficient_data`, not a fairness claim.

## ONNX Serving

The BERT encoder is exported to FP16 ONNX with FP32 I/O. The versioned parity
report includes:

- minimum cosine similarity: 0.9999992
- maximum embedding RMSE: 0.0004651
- maximum absolute element delta: 0.004868
- maximum downstream revenue prediction delta: $0 on three parity samples

The 208 MB ONNX file is stored in GCS, not Git. Its SHA-256 is recorded in
`bert-base-uncased-fp16.parity.json`.

## Monitoring and Promotion

Every forecast stores model version, data cutoff, feature manifest hash,
evidence hashes, confidence, and ledger hash. Monitoring should alert on source
freshness, job failure, feature drift, log-MAE, dollar MAE, interval coverage,
and matched-group normalized error.

No candidate is promoted unless all technical and fairness gates pass. Rollback
means restoring the previous promoted model version; sealed historical
forecasts remain attached to their original version.

# Dataset Card: Phase 5D Real-Factual Benchmark (real_factual_v1)

## Summary
* **Total Cases**: 20
* **Traps Covered**: 10 distinct failure modes (2 cases each)
* **Total Snapshots**: 42
* **Unicode Normalization**: NFC (Python Unicode Code-Point 0-indexed character offsets)
* **Newline Standard**: `\n` (LF)
* **Integrity Gate Status**: 100% VALID

## Trap Breakdown
| Trap Type | Cases | Gold States |
|---|---|---|
| Temporal Supersession | p5d-01, p5d-02 | SUFFICIENT, UNSUPPORTED |
| Geographic Scope | p5d-03, p5d-04 | UNSUPPORTED, SUFFICIENT |
| Republication & Syndication | p5d-05, p5d-06 | INSUFFICIENT, SUFFICIENT |
| Numerical Quantifier | p5d-07, p5d-08 | UNSUPPORTED, SUFFICIENT |
| Exception & Context | p5d-09, p5d-10 | UNSUPPORTED, UNSUPPORTED |
| Negation & Denial | p5d-11, p5d-12 | UNSUPPORTED, UNSUPPORTED |
| Entity & Version | p5d-13, p5d-14 | UNSUPPORTED, UNSUPPORTED |
| Boilerplate & Sidebar | p5d-15, p5d-16 | UNSUPPORTED, UNSUPPORTED |
| Population Restriction | p5d-17, p5d-18 | UNSUPPORTED, UNSUPPORTED |
| Temporal Omission | p5d-19, p5d-20 | UNSUPPORTED, UNSUPPORTED |

## Dataset Integrity & Ethics
- All web snapshots correspond to authentic, published public information.
- Zero manual HTML injection or text tampering.
- Dual-reviewed independent Gold adjudication with 100% rule-consistency validation.

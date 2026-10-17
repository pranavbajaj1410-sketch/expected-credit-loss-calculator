# Expected Credit Loss Calculator

An educational Python project that estimates expected credit loss (ECL) for a portfolio of 1,000 fictional unsecured personal loans. It applies simplified credit-risk staging, calculates loan-level ECL under three scenarios, and combines those results using scenario weights.

## Results

Using the current synthetic dataset and assumptions:

| Scenario | Weight | Portfolio ECL |
|---|---:|---:|
| Upside | 20% | €519,223.69 |
| Base | 60% | €640,805.32 |
| Downside | 20% | €874,065.57 |

The probability-weighted portfolio ECL is approximately **€663,141.04**. Results may change if the model assumptions or dataset are updated.

## Method

- Assigns each loan to Stage 1, 2, or 3 using simplified rules based on days past due, credit impairment, qualitative risk flags, and PD deterioration.
- Uses a 12-month default-risk horizon for Stage 1 and the remaining loan term for Stages 2 and 3.
- Converts annual PD to a constant monthly PD and estimates monthly default risk.
- Estimates exposure using the scheduled loan balance and applies scenario-adjusted LGD.
- Discounts expected losses using the effective interest rate.
- Applies the Upside, Base, and Downside scenario weights to calculate probability-weighted ECL.

## Project files

```text
expected-credit-loss-calculator/
├── data/
│   └── raw/
│       └── synthetic_ecl_dataset.xlsx
├── notebooks/
│   └── ecl_analysis.ipynb
├── outputs/
├── src/
│   └── ecl_calculator.py
├── tests/
│   └── test_ecl_calculator.py
├── requirements.txt
└── README.md

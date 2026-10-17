import math

import pandas as pd


def annual_pd_to_monthly_pd(annual_pd):
    if not 0 <= annual_pd <= 1:
        raise ValueError("Annual PD must be between 0 and 1.")

    return 1 - (1 - annual_pd) ** (1 / 12)


def calculate_loan_ecl(loan_record, scenario_record):
    outstanding_balance = float(loan_record["outstanding_balance"])
    current_pd = float(
        loan_record["current_probability_of_default"]
    )
    loss_given_default = float(loan_record["loss_given_default"])
    pd_multiplier = float(
        scenario_record["annual_pd_multiplier"]
    )
    lgd_multiplier = float(scenario_record["lgd_multiplier"])

    if outstanding_balance < 0:
        raise ValueError("Outstanding balance cannot be negative.")

    if not 0 <= current_pd <= 1:
        raise ValueError("Current PD must be between 0 and 1.")

    if not 0 <= loss_given_default <= 1:
        raise ValueError("LGD must be between 0 and 1.")

    if pd_multiplier < 0 or lgd_multiplier < 0:
        raise ValueError("Scenario multipliers cannot be negative.")

    adjusted_lgd = min(
        loss_given_default * lgd_multiplier,
        1.0,
    )

    if loan_record["credit_impaired"]:
        return outstanding_balance * adjusted_lgd

    adjusted_annual_pd = min(current_pd * pd_multiplier, 1.0)
    monthly_pd = annual_pd_to_monthly_pd(adjusted_annual_pd)

    credit_risk_stage = int(
        loan_record["calculated_credit_risk_stage"]
    )
    remaining_term_months = int(
        loan_record["remaining_term_months"]
    )

    if credit_risk_stage not in (1, 2, 3):
        raise ValueError("Credit risk stage must be 1, 2, or 3.")

    if remaining_term_months < 1:
        raise ValueError("Remaining term must be at least 1 month.")

    if credit_risk_stage == 1:
        calculation_horizon_months = min(
            12,
            remaining_term_months,
        )
    else:
        calculation_horizon_months = remaining_term_months

    balance = outstanding_balance
    monthly_payment = float(
        loan_record["scheduled_monthly_payment"]
    )
    monthly_interest_rate = (
        float(loan_record["annual_interest_rate"]) / 12
    )

    effective_annual_rate = float(
        loan_record["effective_annual_interest_rate"]
    )

    if effective_annual_rate <= -1:
        raise ValueError("Effective annual rate must be greater than -1.")

    monthly_discount_rate = (
        (1 + effective_annual_rate) ** (1 / 12)
    ) - 1

    survival_probability = 1.0
    expected_credit_loss = 0.0

    for month_number in range(
        1,
        calculation_horizon_months + 1,
    ):
        marginal_default_probability = (
            survival_probability * monthly_pd
        )

        discount_factor = (
            1 + monthly_discount_rate
        ) ** (-month_number)

        expected_credit_loss += (
            balance
            * adjusted_lgd
            * marginal_default_probability
            * discount_factor
        )

        survival_probability *= 1 - monthly_pd

        interest_payment = balance * monthly_interest_rate
        principal_payment = min(
            max(monthly_payment - interest_payment, 0.0),
            balance,
        )

        balance = max(balance - principal_payment, 0.0)

        if balance <= 0:
            break

    return expected_credit_loss


def calculate_portfolio_ecl(loan_data, scenario_data):
    required_loan_columns = {
        "loan_id",
        "outstanding_balance",
        "current_probability_of_default",
        "loss_given_default",
        "credit_impaired",
        "calculated_credit_risk_stage",
        "remaining_term_months",
        "scheduled_monthly_payment",
        "annual_interest_rate",
        "effective_annual_interest_rate",
    }

    required_scenario_columns = {
        "scenario",
        "scenario_weight",
        "annual_pd_multiplier",
        "lgd_multiplier",
    }

    missing_loan_columns = required_loan_columns - set(
        loan_data.columns
    )
    missing_scenario_columns = required_scenario_columns - set(
        scenario_data.columns
    )

    if missing_loan_columns:
        raise ValueError(
            f"Loan data is missing columns: {sorted(missing_loan_columns)}"
        )

    if missing_scenario_columns:
        raise ValueError(
            "Scenario data is missing columns: "
            f"{sorted(missing_scenario_columns)}"
        )

    total_scenario_weight = scenario_data["scenario_weight"].sum()

    if not math.isclose(
        total_scenario_weight,
        1.0,
        rel_tol=0,
        abs_tol=1e-9,
    ):
        raise ValueError("Scenario weights must sum to 1.")

    ecl_rows = []

    for loan_record in loan_data.to_dict("records"):
        for scenario_record in scenario_data.to_dict("records"):
            ecl_rows.append(
                {
                    "loan_id": loan_record["loan_id"],
                    "credit_risk_stage": (
                        loan_record["calculated_credit_risk_stage"]
                    ),
                    "scenario": scenario_record["scenario"],
                    "scenario_weight": (
                        scenario_record["scenario_weight"]
                    ),
                    "expected_credit_loss": calculate_loan_ecl(
                        loan_record,
                        scenario_record,
                    ),
                }
            )

    ecl_results = pd.DataFrame(ecl_rows)

    ecl_results["weighted_expected_credit_loss"] = (
        ecl_results["expected_credit_loss"]
        * ecl_results["scenario_weight"]
    )

    return ecl_results
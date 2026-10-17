import unittest

import pandas as pd

from src.ecl_calculator import (
    annual_pd_to_monthly_pd,
    calculate_loan_ecl,
    calculate_portfolio_ecl,
)


def make_loan_record(**overrides):
    loan_record = {
        "loan_id": "TEST001",
        "outstanding_balance": 10_000.0,
        "current_probability_of_default": 0.12,
        "loss_given_default": 0.40,
        "credit_impaired": False,
        "calculated_credit_risk_stage": 1,
        "remaining_term_months": 24,
        "scheduled_monthly_payment": 500.0,
        "annual_interest_rate": 0.12,
        "effective_annual_interest_rate": (
            (1 + 0.12 / 12) ** 12 - 1
        ),
    }

    loan_record.update(overrides)
    return loan_record


def make_scenario_record(**overrides):
    scenario_record = {
        "scenario": "Base",
        "scenario_weight": 1.0,
        "annual_pd_multiplier": 1.0,
        "lgd_multiplier": 1.0,
    }

    scenario_record.update(overrides)
    return scenario_record


class TestEclCalculator(unittest.TestCase):
    def test_monthly_pd_reproduces_annual_pd_over_12_months(self):
        annual_pd = 0.12
        monthly_pd = annual_pd_to_monthly_pd(annual_pd)

        cumulative_pd = 1 - (1 - monthly_pd) ** 12

        self.assertAlmostEqual(cumulative_pd, annual_pd)

    def test_stage_1_uses_only_12_months_of_default_risk(self):
        scenario_record = make_scenario_record()

        loan_with_24_months = make_loan_record(
            calculated_credit_risk_stage=1,
            remaining_term_months=24,
        )
        loan_with_12_months = make_loan_record(
            calculated_credit_risk_stage=1,
            remaining_term_months=12,
        )

        ecl_24_months = calculate_loan_ecl(
            loan_with_24_months,
            scenario_record,
        )
        ecl_12_months = calculate_loan_ecl(
            loan_with_12_months,
            scenario_record,
        )

        self.assertAlmostEqual(ecl_24_months, ecl_12_months)

    def test_lifetime_ecl_is_higher_than_12_month_ecl(self):
        scenario_record = make_scenario_record()

        stage_1_loan = make_loan_record(
            calculated_credit_risk_stage=1,
        )
        stage_2_loan = make_loan_record(
            calculated_credit_risk_stage=2,
        )

        stage_1_ecl = calculate_loan_ecl(
            stage_1_loan,
            scenario_record,
        )
        stage_2_ecl = calculate_loan_ecl(
            stage_2_loan,
            scenario_record,
        )

        self.assertGreater(stage_2_ecl, stage_1_ecl)

    def test_credit_impaired_loan_uses_reporting_date_lgd(self):
        loan_record = make_loan_record(
            credit_impaired=True,
        )
        scenario_record = make_scenario_record(
            lgd_multiplier=0.9,
        )

        expected_ecl = (
            loan_record["outstanding_balance"]
            * loan_record["loss_given_default"]
            * 0.9
        )

        actual_ecl = calculate_loan_ecl(
            loan_record,
            scenario_record,
        )

        self.assertAlmostEqual(actual_ecl, expected_ecl)

    def test_downside_scenario_has_higher_ecl_than_upside(self):
        loan_record = make_loan_record()

        upside_ecl = calculate_loan_ecl(
            loan_record,
            make_scenario_record(
                annual_pd_multiplier=0.75,
                lgd_multiplier=0.9,
            ),
        )
        downside_ecl = calculate_loan_ecl(
            loan_record,
            make_scenario_record(
                annual_pd_multiplier=1.5,
                lgd_multiplier=1.15,
            ),
        )

        self.assertGreater(downside_ecl, upside_ecl)

    def test_portfolio_calculation_returns_one_row_per_scenario(self):
        loan_data = pd.DataFrame(
            [
                make_loan_record(),
                make_loan_record(loan_id="TEST002"),
            ]
        )

        scenario_data = pd.DataFrame(
            [
                make_scenario_record(
                    scenario="Upside",
                    scenario_weight=0.2,
                    annual_pd_multiplier=0.75,
                    lgd_multiplier=0.9,
                ),
                make_scenario_record(
                    scenario="Base",
                    scenario_weight=0.6,
                ),
                make_scenario_record(
                    scenario="Downside",
                    scenario_weight=0.2,
                    annual_pd_multiplier=1.5,
                    lgd_multiplier=1.15,
                ),
            ]
        )

        results = calculate_portfolio_ecl(
            loan_data,
            scenario_data,
        )

        self.assertEqual(len(results), 6)
        self.assertTrue(
            (results["expected_credit_loss"] >= 0).all()
        )
        self.assertTrue(
            (results["weighted_expected_credit_loss"] >= 0).all()
        )


if __name__ == "__main__":
    unittest.main()
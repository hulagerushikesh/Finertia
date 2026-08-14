"""Request validation — the rules that stop a bad backtest before it starts."""

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from schemas import (
    BacktestRequest,
    ValidateRequest,
    CompareRequest,
    PortfolioRequest,
    UserPatch,
    RISK_KEYS,
)


def req(**overrides):
    base = {"ticker": "AAPL", "start": "2018-01-01", "end": "2023-01-01"}
    base.update(overrides)
    return BacktestRequest(**base)


def message(exc_info):
    return str(exc_info.value)


class TestTicker:
    def test_uppercased_and_trimmed(self):
        assert req(ticker="  aapl  ").ticker == "AAPL"

    def test_blank_is_rejected(self):
        with pytest.raises(ValidationError, match="Ticker is required"):
            req(ticker="   ")

    def test_overlong_is_rejected(self):
        with pytest.raises(ValidationError, match="12 characters"):
            req(ticker="A" * 13)

    def test_illegal_characters_are_rejected(self):
        with pytest.raises(ValidationError, match="letters, digits"):
            req(ticker="AA;DROP")

    @pytest.mark.parametrize("symbol", ["BRK.B", "RDS-A", "^GSPC", "EURUSD=X"])
    def test_real_world_symbol_formats_are_allowed(self, symbol):
        assert req(ticker=symbol).ticker == symbol


class TestDates:
    def test_malformed_date_is_rejected(self):
        with pytest.raises(ValidationError, match="not a valid date"):
            req(start="01-01-2018")

    def test_start_must_precede_end(self):
        with pytest.raises(ValidationError, match="Start date must be before end date"):
            req(start="2023-01-01", end="2018-01-01")

    def test_identical_dates_are_rejected(self):
        with pytest.raises(ValidationError, match="before end date"):
            req(start="2020-01-01", end="2020-01-01")

    def test_future_end_date_is_rejected(self):
        future = (date.today() + timedelta(days=30)).isoformat()
        with pytest.raises(ValidationError, match="cannot be in the future"):
            req(end=future)

    def test_range_shorter_than_warmup_is_rejected(self):
        with pytest.raises(ValidationError, match="too short"):
            req(start="2022-01-01", end="2022-03-01", ma_window=200)

    def test_error_names_the_strategy_and_its_requirement(self):
        with pytest.raises(ValidationError) as e:
            req(start="2022-01-01", end="2022-02-01", strategy="bollinger", bb_window=100)
        assert "bollinger" in message(e) and "100 bars" in message(e)


class TestStrategySelection:
    def test_defaults_to_momentum(self):
        assert req().strategy == "momentum"

    def test_case_and_whitespace_are_normalised(self):
        assert req(strategy="  MACD  ").strategy == "macd"

    def test_unknown_strategy_lists_the_valid_options(self):
        with pytest.raises(ValidationError) as e:
            req(strategy="rsi")
        for name in ("momentum", "macd", "bollinger"):
            assert name in message(e)


class TestStrategyParams:
    def test_momentum_exposes_only_its_own_fields(self):
        assert set(req(strategy="momentum").strategy_params()) == {
            "momentum_lookback", "ma_window", "momentum_threshold"
        }

    def test_macd_exposes_only_its_own_fields(self):
        assert set(req(strategy="macd").strategy_params()) == {
            "macd_fast", "macd_slow", "macd_signal"
        }

    def test_bollinger_exposes_only_its_own_fields(self):
        assert set(req(strategy="bollinger").strategy_params()) == {"bb_window", "bb_std"}

    def test_other_strategies_fields_are_never_leaked(self):
        params = req(strategy="bollinger", momentum_lookback=99, macd_fast=7).strategy_params()
        assert "momentum_lookback" not in params
        assert "macd_fast" not in params

    def test_values_carry_through(self):
        assert req(strategy="macd", macd_fast=5, macd_slow=40).strategy_params() == {
            "macd_fast": 5, "macd_slow": 40, "macd_signal": 9
        }


class TestMacdSpecific:
    def test_fast_must_be_shorter_than_slow(self):
        with pytest.raises(ValidationError, match="fast period must be shorter"):
            req(strategy="macd", macd_fast=30, macd_slow=26)

    def test_equal_periods_are_rejected(self):
        with pytest.raises(ValidationError, match="fast period must be shorter"):
            req(strategy="macd", macd_fast=26, macd_slow=26)

    def test_inverted_periods_are_ignored_for_other_strategies(self):
        # The fields still exist but are not this strategy's concern.
        assert req(strategy="momentum", macd_fast=30, macd_slow=26).strategy == "momentum"


class TestNumericBounds:
    @pytest.mark.parametrize("field,value", [
        ("momentum_lookback", 4), ("momentum_lookback", 201),
        ("ma_window", 4), ("ma_window", 301),
        ("transaction_cost", -0.1), ("transaction_cost", 0.5),
        ("momentum_threshold", -0.1), ("momentum_threshold", 1.5),
        ("bb_std", 0.1), ("bb_std", 5.0),
        ("macd_signal", 1), ("macd_signal", 101),
    ])
    def test_out_of_range_values_are_rejected(self, field, value):
        with pytest.raises(ValidationError):
            req(**{field: value})

    def test_boundary_values_are_accepted(self):
        assert req(momentum_lookback=5, ma_window=5, transaction_cost=0.0).momentum_lookback == 5


class TestValidateRequest:
    def test_inherits_every_backtest_rule(self):
        with pytest.raises(ValidationError, match="cannot be in the future"):
            ValidateRequest(
                ticker="AAPL", start="2018-01-01",
                end=(date.today() + timedelta(days=5)).isoformat(),
            )

    def test_split_and_trial_defaults(self):
        v = ValidateRequest(ticker="AAPL", start="2018-01-01", end="2023-01-01")
        assert v.split_ratio == 0.7
        assert v.permutation_trials == 500

    @pytest.mark.parametrize("ratio", [0.4, 0.95])
    def test_split_ratio_bounds(self, ratio):
        with pytest.raises(ValidationError):
            ValidateRequest(ticker="AAPL", start="2018-01-01", end="2023-01-01", split_ratio=ratio)

    @pytest.mark.parametrize("trials", [50, 5000])
    def test_permutation_trial_bounds(self, trials):
        with pytest.raises(ValidationError):
            ValidateRequest(
                ticker="AAPL", start="2018-01-01", end="2023-01-01", permutation_trials=trials
            )


class TestRiskOverlays:
    def test_overlays_are_off_by_default(self):
        r = req()
        assert r.stop_loss is None and r.take_profit is None and r.sizing == "fixed"

    def test_accepts_a_stop_and_target(self):
        r = req(stop_loss=0.05, take_profit=0.15)
        assert (r.stop_loss, r.take_profit) == (0.05, 0.15)

    @pytest.mark.parametrize("bad", [0, -0.05, 0.95])
    def test_rejects_out_of_range_stop_loss(self, bad):
        with pytest.raises(ValidationError):
            req(stop_loss=bad)

    def test_rejects_a_target_no_further_than_the_stop(self):
        # A 5% target behind a 10% stop closes on noise every time.
        with pytest.raises(ValidationError, match="further from entry"):
            req(stop_loss=0.10, take_profit=0.05)

    def test_allows_a_target_wider_than_the_stop(self):
        assert req(stop_loss=0.05, take_profit=0.06).take_profit == 0.06

    @pytest.mark.parametrize("rule", ["fixed", "vol_target"])
    def test_accepts_known_sizing_rules(self, rule):
        assert req(sizing=rule).sizing == rule

    def test_normalises_sizing_case(self):
        assert req(sizing="  VOL_TARGET ").sizing == "vol_target"

    def test_rejects_an_unknown_sizing_rule(self):
        with pytest.raises(ValidationError, match="fixed"):
            req(sizing="kelly")

    def test_risk_params_covers_every_declared_key(self):
        # Guards the split in /api/compare: a new overlay field that risk_params
        # forgets would be handed to the signal builder and silently ignored.
        assert set(req().risk_params()) == set(RISK_KEYS)

    def test_risk_and_strategy_params_never_overlap(self):
        r = req()
        assert not set(r.risk_params()) & set(r.strategy_params())

    def test_warmup_ignores_the_vol_window_under_fixed_sizing(self):
        assert req(sizing="fixed", ma_window=50, vol_window=200).warmup_bars() == 50

    def test_warmup_counts_the_vol_window_when_targeting(self):
        # Without this a range long enough for the signal but not the sizing
        # returns an all-flat backtest with no explanation.
        assert req(sizing="vol_target", ma_window=50, vol_window=200).warmup_bars() == 200

    def test_range_too_short_for_the_vol_window_is_rejected(self):
        with pytest.raises(ValidationError, match="warm up"):
            req(start="2022-01-01", end="2022-06-01", sizing="vol_target", vol_window=200)

    def test_error_blames_sizing_when_sizing_is_the_binding_constraint(self):
        # Saying "this config needs 200 bars" leaves the user guessing which
        # knob to turn; the message has to name the one that is actually binding.
        with pytest.raises(ValidationError) as e:
            req(start="2022-01-01", end="2022-06-01", ma_window=10,
                sizing="vol_target", vol_window=200)
        assert "volatility targeting" in message(e)


def port(**overrides):
    base = {"tickers": ["AAPL", "MSFT"], "start": "2018-01-01", "end": "2023-01-01"}
    base.update(overrides)
    return PortfolioRequest(**base)


class TestPortfolioRequest:
    def test_accepts_two_tickers(self):
        assert port().tickers == ["AAPL", "MSFT"]

    def test_accepts_the_maximum_of_ten(self):
        assert len(port(tickers=[f"T{i}" for i in range(10)]).tickers) == 10

    def test_rejects_a_single_ticker(self):
        with pytest.raises(ValidationError):
            port(tickers=["AAPL"])

    def test_rejects_more_than_ten(self):
        with pytest.raises(ValidationError):
            port(tickers=[f"T{i}" for i in range(11)])

    def test_rejects_a_repeated_ticker(self):
        # Holding a name twice is a bigger position, not a second holding.
        with pytest.raises(ValidationError, match="more than once"):
            port(tickers=["AAPL", "AAPL"])

    def test_normalises_case_and_whitespace(self):
        assert port(tickers=[" aapl ", "msft\n"]).tickers == ["AAPL", "MSFT"]

    def test_rejects_an_invalid_symbol(self):
        with pytest.raises(ValidationError, match="not a valid ticker"):
            port(tickers=["AAPL", "BAD;DROP"])

    def test_real_world_symbols_are_allowed(self):
        assert port(tickers=["BRK.B", "^GSPC"]).tickers == ["BRK.B", "^GSPC"]

    def test_seeds_the_inherited_ticker_field(self):
        # The parent's date and warm-up checks need a ticker to work with.
        assert port().ticker == "AAPL"

    def test_inherits_every_backtest_rule(self):
        with pytest.raises(ValidationError, match="cannot be in the future"):
            port(end=(date.today() + timedelta(days=5)).isoformat())

    def test_inherits_the_risk_overlay_rules(self):
        with pytest.raises(ValidationError, match="further from entry"):
            port(stop_loss=0.10, take_profit=0.05)

    @pytest.mark.parametrize("rule", ["equal", "inverse_vol"])
    def test_accepts_known_weightings(self, rule):
        assert port(weighting=rule).weighting == rule

    def test_normalises_weighting_case(self):
        assert port(weighting=" INVERSE_VOL ").weighting == "inverse_vol"

    def test_rejects_an_unknown_weighting(self):
        with pytest.raises(ValidationError, match="equal"):
            port(weighting="risk_parity")

    def test_rejects_a_cap_too_small_to_fill_the_book(self):
        with pytest.raises(ValidationError, match="cannot fill a book"):
            port(tickers=["A", "B", "C"], max_weight=0.3)

    def test_accepts_a_cap_exactly_large_enough(self):
        assert port(tickers=["A", "B", "C"], max_weight=1 / 3 + 1e-9).max_weight > 0.33

    def test_warmup_ignores_the_weight_window_under_equal_weighting(self):
        assert port(weighting="equal", ma_window=50, weight_window=200).warmup_bars() == 50

    def test_warmup_counts_the_weight_window_when_inverse_vol(self):
        assert (
            port(weighting="inverse_vol", ma_window=50, weight_window=200).warmup_bars() == 200
        )

    def test_warmup_takes_the_largest_of_all_three_windows(self):
        # Signal, position sizing, and weighting each impose their own.
        r = port(
            weighting="inverse_vol", ma_window=30,
            sizing="vol_target", vol_window=120, weight_window=90,
        )
        assert r.warmup_bars() == 120

    def test_range_too_short_for_the_weight_window_is_rejected(self):
        with pytest.raises(ValidationError, match="warm up"):
            port(start="2022-01-01", end="2022-06-01",
                 weighting="inverse_vol", weight_window=200)


class TestCompareRequest:
    def test_accepts_two_runs(self):
        assert CompareRequest(run_ids=["a", "b"]).run_ids == ["a", "b"]

    def test_accepts_the_maximum_of_four(self):
        assert len(CompareRequest(run_ids=["a", "b", "c", "d"]).run_ids) == 4

    def test_rejects_a_single_run(self):
        with pytest.raises(ValidationError):
            CompareRequest(run_ids=["a"])

    def test_rejects_more_than_four(self):
        with pytest.raises(ValidationError):
            CompareRequest(run_ids=["a", "b", "c", "d", "e"])

    def test_rejects_duplicates(self):
        # Comparing a run against itself draws one line twice and reads as a bug.
        with pytest.raises(ValidationError, match="more than once"):
            CompareRequest(run_ids=["a", "a"])

    def test_strips_surrounding_whitespace(self):
        assert CompareRequest(run_ids=[" a ", "b\n"]).run_ids == ["a", "b"]

    def test_blank_entries_do_not_count_toward_the_minimum(self):
        with pytest.raises(ValidationError, match="at least two"):
            CompareRequest(run_ids=["a", "   "])


class TestUserPatch:
    def test_both_fields_optional(self):
        assert UserPatch().isActive is None and UserPatch().role is None

    def test_accepts_partial_updates(self):
        assert UserPatch(isActive=False).isActive is False
        assert UserPatch(role="admin").role == "admin"

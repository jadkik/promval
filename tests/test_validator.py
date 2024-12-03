import re

import pytest

from promval import PromQLSyntaxError
from promval.error import ValidationError
from promval.validator import (
    AggregationGroupValidator,
    AggregationLabelValueValidator,
    AggregationFunctionValidator,
    FunctionValidator,
)


def test_group_by_validator_valid():
    expr = """
        sum by (job) (
          rate(http_requests_total[5m])
        )
    """
    validator = AggregationGroupValidator(expected={"job"})
    validator.validate(expr)


def test_group_without_validator_valid():
    expr = """
        sum without (job) (
          rate(http_requests_total[5m])
        )
    """
    validator = AggregationGroupValidator(expected={"job"})
    validator.validate(expr)


def test_group_validator_complex():
    expr = """
        sum by (group, name)
        (
            sum_over_time(
                label_replace(some_metric, "name", "$1", "othername", "(.*)")[6h:]
            )
        ) > 5
    """
    validator = AggregationGroupValidator(expected={"name", "group"})
    validator.validate(expr)


def test_group_validator_missing_group():
    expr = """
        sum by (job) (
          rate(http_requests_total[5m])
        )
    """
    validator = AggregationGroupValidator(expected={"job", "thing"})
    with pytest.raises(ValidationError):
        validator.validate(expr)


def test_group_validator_combined_query():
    expr = """
        max by (very, second)(foo_metric{very=~'important', something='else'}) > 0
        and on (host,project)(metric_name) > 0
    """
    validator = AggregationGroupValidator(expected={"job", "thing"})
    with pytest.raises(ValidationError):
        validator.validate(expr)


def test_label_value_validator_valid():
    expr = """
        max by (very, second)(foo_metric{very=~'important', something='else'})
    """
    validator = AggregationLabelValueValidator(label_value="important")
    validator.validate(expr)


def test_label_value_validator_missing_label():
    expr = """
        max by (ve, second)(foo_metric{very=~'important', something='else'})
    """
    validator = AggregationLabelValueValidator(label_value="important")
    with pytest.raises(ValidationError):
        validator.validate(expr)


def test_label_value_validator_multiple_labels():
    expr = """
        avg by (first, second)(foo_metric{very=~'important'} / foo_metric{very=~'important'}) > 8
    """
    validator = AggregationLabelValueValidator(label_value="important")
    with pytest.raises(ValidationError):
        validator.validate(expr)


def test_agg_function_validator():
    expr = """
        avg by (group, name)
        (
            absent_over_time(
                label_replace(some_metric, "name", "$1", "othername", "(.*)")[6h:]
            )
        ) > 5
    """
    validator = AggregationFunctionValidator(blacklisted={"avg"})
    with pytest.raises(ValidationError, match="using blacklisted aggregator"):
        validator.validate(expr)


def test_new_agg_function_validator():
    """Regression test: present_over_time is parsed correctly; it has been added after absent_over_time was."""
    expr = """
        avg by (group, name)
        (
            present_over_time(
                label_replace(some_metric, "name", "$1", "othername", "(.*)")[6h:]
            )
        ) > 5
    """
    validator = AggregationFunctionValidator(blacklisted={"avg"})
    with pytest.raises(ValidationError, match="using blacklisted aggregator"):
        validator.validate(expr)


def test_unsupported_agg_function_validator_fails():
    """Test that aggregation functions that are not supported by the lexer fail at the parsing stage."""
    expr = """
        avg by (group, name)
        (
            unsupported_aggregation_over_time(
                label_replace(some_metric, "name", "$1", "othername", "(.*)")[6h:]
            )
        ) > 5
    """
    validator = AggregationFunctionValidator(blacklisted={"avg"})
    with pytest.raises(
        PromQLSyntaxError, match=re.escape("mismatched input '(' expecting {')', ','}")
    ):
        validator.validate(expr)


def test_function_validator():
    expr = """
        avg by (group, name)
        (
            absent_over_time(
                label_replace(some_metric, "name", "$1", "othername", "(.*)")[6h:]
            )
        ) > 5
    """
    validator = FunctionValidator(blacklisted={"absent", "absent_over_time"})
    with pytest.raises(ValidationError):
        validator.validate(expr)

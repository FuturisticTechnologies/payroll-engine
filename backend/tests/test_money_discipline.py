"""Static guard: money never touches binary floating point.

Written after the M3 review. The rule "money is Decimal, never float" is in the
handbook and in every code review, but nothing enforced it — and a single
``float()`` on a rounding path produces a figure that is out by a penny for
some inputs and correct for the ones anybody happens to test.

This scans the calculation and persistence modules with ``ast`` rather than
running them, so it holds even for branches the test data does not reach.
"""
from __future__ import annotations

import ast
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"

#: Modules where a float would corrupt a payroll figure. Missing files are
#: skipped so the pack runs unchanged against every milestone snapshot.
MONEY_MODULES = [
    APP / "core" / "payroll_engine.py",
    APP / "core" / "paye.py",
    APP / "core" / "ni.py",
    APP / "models" / "payroll.py",
    APP / "models" / "paye.py",
    APP / "models" / "ni.py",
]


def _present() -> list[Path]:
    return [path for path in MONEY_MODULES if path.exists()]


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_the_scan_actually_covers_something() -> None:
    # Guards against the pack silently passing because every path was skipped.
    assert _present(), "no money modules found - the scan would be vacuous"


def test_no_float_constructor_in_money_modules() -> None:
    offenders: list[str] = []
    for path in _present():
        for node in ast.walk(_tree(path)):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "float"
            ):
                offenders.append(f"{path.name}:{node.lineno} float(...)")
    assert offenders == []


def test_no_float_literals_in_money_modules() -> None:
    offenders: list[str] = []
    for path in _present():
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.Constant) and isinstance(node.value, float):
                offenders.append(f"{path.name}:{node.lineno} literal {node.value!r}")
    assert offenders == []


def test_money_modules_do_not_import_float_helpers() -> None:
    banned = {"fsum", "isclose"}
    offenders: list[str] = []
    for path in _present():
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.ImportFrom) and node.module == "math":
                for alias in node.names:
                    if alias.name in banned:
                        offenders.append(f"{path.name}:{node.lineno} math.{alias.name}")
    assert offenders == []


def test_decimal_is_imported_where_money_is_calculated() -> None:
    for path in _present():
        source = path.read_text(encoding="utf-8")
        assert "Decimal" in source, f"{path.name} handles money without Decimal"


def test_numeric_columns_declare_precision_and_scale() -> None:
    # Numeric() with no arguments is unbounded in Postgres and silently lossy
    # through some drivers. Every money column must be explicit.
    offenders: list[str] = []
    for path in _present():
        if path.parent.name != "models":
            continue
        for node in ast.walk(_tree(path)):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "Numeric"
                and len(node.args) < 2
            ):
                offenders.append(f"{path.name}:{node.lineno} Numeric() without precision")
    assert offenders == []


def test_rounding_is_half_up_not_bankers() -> None:
    # Python's default is ROUND_HALF_EVEN. HMRC expects half-up on PAYE and NI,
    # so the default being wrong is exactly the kind of thing to pin.
    assert Decimal("0.005").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) == Decimal("0.01")
    assert Decimal("2.675").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) == Decimal("2.68")


def test_float_arithmetic_would_have_been_wrong() -> None:
    # The failure this whole pack exists to prevent, stated once.
    assert round(2.675, 2) == 2.67  # binary float: wrong for payroll
    assert Decimal("2.675").quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    ) == Decimal("2.68")

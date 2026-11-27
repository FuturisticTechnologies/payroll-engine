"""Build the statutory reference data review workbook from the seed CSV.

    python analytics/statutory-reference/build_review_workbook.py

Re-run after every change to backend/app/reference_data/statutory_payment_rates.csv
and commit the regenerated .xlsx with it. Every derived figure in the workbook
is an Excel formula over the Rates sheet, so a reviewer can change an input or
paste in next year's rows and watch the checks respond.
"""
from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "backend" / "app" / "reference_data" / "statutory_payment_rates.csv"
OUT_PATH = Path(__file__).resolve().parent / "statutory_payment_rates_review.xlsx"

LAST = 60  # Rates rows 2..LAST are scanned, leaving room for future tax years
FONT = "Arial"
HEADER_FILL = PatternFill("solid", fgColor="1F3864")
INPUT_FILL = PatternFill("solid", fgColor="FFF2CC")
PASS_FILL = PatternFill("solid", fgColor="C6EFCE")
FAIL_FILL = PatternFill("solid", fgColor="FFC7CE")
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

INT_FIELDS = {
    "tax_year", "period_start_week", "period_end_week", "relevant_period_weeks",
    "qualifying_week_offset_weeks", "continuous_employment_weeks", "waiting_days",
    "max_entitlement_weeks", "payment_window_weeks",
}
MONEY_FIELDS = {"weekly_flat_rate", "lower_earnings_limit_weekly"}


def font(**kw: object) -> Font:
    return Font(name=FONT, **kw)  # type: ignore[arg-type]


def header(ws, row: int, values: list[str]) -> None:  # type: ignore[no-untyped-def]
    for col, value in enumerate(values, start=1):
        cell = ws.cell(row=row, column=col, value=value)
        cell.font = font(bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        cell.border = BOX


def rng(col: str) -> str:
    return f"Rates!${col}$2:${col}${LAST}"


def read_rows() -> tuple[list[str], list[dict[str, str]]]:
    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def build() -> None:
    fields, rows = read_rows()
    col = {name: get_column_letter(i) for i, name in enumerate(fields, start=1)}
    wb = Workbook()

    # ------------------------------------------------------------- README --
    ws = wb.active
    ws.title = "README"
    lines = [
        ("Statutory payment reference data - review workbook", True),
        ("SNOV-442 · SSP, SMP and SPP rates, thresholds and limits, effective-dated by tax year", False),
        ("", False),
        ("Sheets", True),
        ("Rates - the seed rows, one per scheme / rate period / tax year (copy of the CSV)", False),
        ("Calculator - enter a pay date and earnings (yellow cells); every figure is looked up from Rates", False),
        ("Year on year - 2025/26 against 2026/27 for each headline value", False),
        ("Checks - PASS / FAIL data quality tests over every row in Rates", False),
        ("", False),
        ("How to review a new tax year", True),
        ("1. Paste the updated CSV rows into Rates (keep the header row).", False),
        ("2. Every row on Checks must read PASS.", False),
        ("3. Compare Rates against the HMRC page in source_url, row by row, and initial the review.", False),
        ("", False),
        ("Source of truth: backend/app/reference_data/statutory_payment_rates.csv", False),
        ("Regenerate: python analytics/statutory-reference/build_review_workbook.py", False),
        ("Yellow cells are inputs. Everything else is a formula or a copy of the CSV.", False),
    ]
    for i, (text, bold) in enumerate(lines, start=1):
        ws.cell(row=i, column=1, value=text).font = font(bold=bold, size=14 if i == 1 else 10)
    ws.column_dimensions["A"].width = 110

    # -------------------------------------------------------------- Rates --
    rates = wb.create_sheet("Rates")
    header(rates, 1, fields)
    for r, row in enumerate(rows, start=2):
        for c, name in enumerate(fields, start=1):
            raw = row[name]
            if raw == "":
                value: object = None
            elif name in INT_FIELDS:
                value = int(raw)
            elif name in {"effective_from", "effective_to"}:
                value = date.fromisoformat(raw)
            elif name in MONEY_FIELDS or name == "awe_percentage":
                value = float(Decimal(raw))
            else:
                value = raw
            cell = rates.cell(row=r, column=c, value=value)
            cell.font = font(size=10)
            cell.border = BOX
            if name in {"effective_from", "effective_to"}:
                cell.number_format = "yyyy-mm-dd"
            elif name in MONEY_FIELDS:
                cell.number_format = "£#,##0.00"
            elif name == "awe_percentage":
                cell.number_format = "0%"
    widths = {"source_reference": 60, "source_url": 55, "rate_rule": 28, "rate_period": 16}
    for name, letter in col.items():
        rates.column_dimensions[letter].width = widths.get(name, 13)
    rates.freeze_panes = "D2"
    rates.auto_filter.ref = f"A1:{get_column_letter(len(fields))}{len(rows) + 1}"
    rates[f"{col['weekly_flat_rate']}1"].comment = Comment(
        "Source: HMRC Rates and thresholds for employers (see source_url per row).", "SNOV-442"
    )

    # --------------------------------------------------------- Calculator --
    calc = wb.create_sheet("Calculator")
    calc["A1"] = "Statutory pay calculator - values in force on the pay date"
    calc["A1"].font = font(bold=True, size=13)
    inputs = [
        ("Pay date (week being paid)", date(2026, 6, 1), "yyyy-mm-dd"),
        ("Average weekly earnings (£)", 500, "£#,##0.00"),
        ("SSP qualifying days per week", 5, "0"),
        ("SSP qualifying days of sickness in the spell", 3, "0"),
    ]
    for i, (label, value, fmt) in enumerate(inputs, start=3):
        calc.cell(row=i, column=1, value=label).font = font()
        cell = calc.cell(row=i, column=2, value=value)
        cell.font = font(color="0000FF")
        cell.fill = INPUT_FILL
        cell.number_format = fmt
        cell.border = BOX
    dv = DataValidation(type="whole", operator="between", formula1="1", formula2="7")
    calc.add_data_validation(dv)
    dv.add("B5")

    header(calc, 8, [
        "Scheme", "Rate period", "Rates row", "Tax year", "From", "To", "% of AWE",
        "Weekly flat rate", "Rule", "LEL (weekly)", "Earnings test", "Weekly amount",
        "Waiting days", "Max weeks", "Source",
    ])
    lookups = [("SSP", "standard"), ("SMP", "first_6_weeks"), ("SMP", "remaining_weeks"), ("SPP", "standard")]
    for i, (scheme, period) in enumerate(lookups, start=9):
        calc.cell(row=i, column=1, value=scheme)
        calc.cell(row=i, column=2, value=period)
        calc.cell(row=i, column=3, value=(
            f"=SUMPRODUCT(({rng(col['scheme'])}=A{i})*({rng(col['rate_period'])}=B{i})"
            f"*({rng(col['effective_from'])}<=$B$3)*({rng(col['effective_to'])}>=$B$3)"
            f"*ROW({rng(col['scheme'])}))"
        ))

        def pick(field: str, r: int = i) -> str:
            return f'IF($C{r}=0,"",INDEX(Rates!${col[field]}:${col[field]},$C{r}))'

        calc.cell(row=i, column=4, value="=" + pick("tax_year"))
        calc.cell(row=i, column=5, value="=" + pick("effective_from"))
        calc.cell(row=i, column=6, value="=" + pick("effective_to"))
        def pick_blank(field: str, r: int = i) -> str:
            ref = f"INDEX(Rates!${col[field]}:${col[field]},$C{r})"
            return f'=IF($C{r}=0,"",IF({ref}="","",{ref}))'

        calc.cell(row=i, column=7, value=pick_blank("awe_percentage"))
        calc.cell(row=i, column=8, value=pick_blank("weekly_flat_rate"))
        calc.cell(row=i, column=9, value="=" + pick("rate_rule"))
        lel = f"INDEX(Rates!${col['lower_earnings_limit_weekly']}:${col['lower_earnings_limit_weekly']},$C{i})"
        calc.cell(row=i, column=10, value=f'=IF($C{i}=0,"",IF({lel}="","none",{lel}))')
        calc.cell(row=i, column=11, value=f'=IF($C{i}=0,"NO DATA",IF(J{i}="none","no earnings test",IF($B$4>=J{i},"meets LEL","below LEL")))')
        calc.cell(row=i, column=12, value=(
            f'=IF($C{i}=0,"",IF(K{i}="below LEL",0,ROUNDUP('
            f'IF(I{i}="flat_rate_only",H{i},IF(I{i}="percentage_only",$B$4*G{i},MIN(H{i},$B$4*G{i}))),2)))'
        ))
        calc.cell(row=i, column=13, value="=" + pick("waiting_days"))
        calc.cell(row=i, column=14, value="=" + pick("max_entitlement_weeks"))
        calc.cell(row=i, column=15, value="=" + pick("source_url"))
        for c in range(1, 16):
            cell = calc.cell(row=i, column=c)
            cell.font = font(size=10)
            cell.border = BOX
        calc[f"E{i}"].number_format = calc[f"F{i}"].number_format = "yyyy-mm-dd"
        calc[f"G{i}"].number_format = "0%"
        calc[f"H{i}"].number_format = calc[f"J{i}"].number_format = "£#,##0.00"
        calc[f"L{i}"].number_format = "£#,##0.00"

    calc["A15"] = "SSP for the spell"
    calc["A15"].font = font(bold=True)
    calc["A16"] = "Payable days (sick days less waiting days)"
    calc["B16"] = '=IF(C9=0,"",MAX($B$6-M9,0))'
    calc["A17"] = "Daily rate (unrounded)"
    calc["B17"] = (
        '=IF(C9=0,"",IF(I9="flat_rate_only",H9,'
        'IF(I9="percentage_only",$B$4*G9,MIN(H9,$B$4*G9)))/$B$5)'
    )
    calc["A18"] = "SSP due (rounded up to the penny)"
    calc["B18"] = '=IF(C9=0,"",IF(K9="below LEL",0,ROUNDUP(B17*B16,2)))'
    calc["A20"] = "SMP over the full entitlement"
    calc["A20"].font = font(bold=True)
    calc["A21"] = "Weeks at the first-period amount"
    calc["B21"] = '=IF(C10=0,"",INDEX(Rates!$E:$E,C10)-INDEX(Rates!$D:$D,C10)+1)'
    calc["A22"] = "Weeks at the remaining-period amount"
    calc["B22"] = '=IF(C11=0,"",INDEX(Rates!$E:$E,C11)-INDEX(Rates!$D:$D,C11)+1)'
    calc["A23"] = "Total SMP"
    calc["B23"] = '=IF(OR(C10=0,C11=0),"",B21*L10+B22*L11)'
    calc["A24"] = "Total SPP (full entitlement)"
    calc["B24"] = '=IF(C12=0,"",L12*N12)'
    for ref in ("B16",):
        calc[ref].number_format = "0"
    calc["B17"].number_format = "£#,##0.0000"
    for ref in ("B18", "B23", "B24"):
        calc[ref].number_format = "£#,##0.00"
    for ref in ("B21", "B22"):
        calc[ref].number_format = "0"
    for r in range(16, 25):
        for c in (1, 2):
            calc.cell(row=r, column=c).font = font(size=10)
    calc["A26"] = (
        "Rates row = 0 means nothing is in force on the pay date: the engine refuses to pay "
        "rather than borrow another year's rate."
    )
    calc["A26"].font = font(italic=True, size=9, color="595959")
    calc.column_dimensions["A"].width = 44
    for letter in "BCDEFGHIJKLMN":
        calc.column_dimensions[letter].width = 14
    calc.column_dimensions["I"].width = 28
    calc.column_dimensions["O"].width = 60

    # ------------------------------------------------------- Year on year --
    yoy = wb.create_sheet("Year on year")
    header(yoy, 1, ["Measure", "Scheme", "Rate period", "Field", "2025/26", "2026/27", "Change", "% change"])
    measures = [
        ("SSP weekly flat rate", "SSP", "standard", "weekly_flat_rate", "money"),
        ("SSP % of AWE cap", "SSP", "standard", "awe_percentage", "pct"),
        ("SSP lower earnings limit", "SSP", "standard", "lower_earnings_limit_weekly", "money"),
        ("SSP waiting days", "SSP", "standard", "waiting_days", "int"),
        ("SMP remaining-weeks flat rate", "SMP", "remaining_weeks", "weekly_flat_rate", "money"),
        ("SMP lower earnings limit", "SMP", "first_6_weeks", "lower_earnings_limit_weekly", "money"),
        ("SPP weekly flat rate", "SPP", "standard", "weekly_flat_rate", "money"),
        ("SPP lower earnings limit", "SPP", "standard", "lower_earnings_limit_weekly", "money"),
    ]
    for i, (label, scheme, period, field, kind) in enumerate(measures, start=2):
        yoy.cell(row=i, column=1, value=label)
        yoy.cell(row=i, column=2, value=scheme)
        yoy.cell(row=i, column=3, value=period)
        yoy.cell(row=i, column=4, value=field)
        for c, year in ((5, 2025), (6, 2026)):
            crit = (
                f'{rng(col["tax_year"])},{year},{rng(col["scheme"])},$B{i},'
                f'{rng(col["rate_period"])},$C{i}'
            )
            yoy.cell(row=i, column=c, value=(
                f'=IF(COUNTIFS({crit},{rng(col[field])},"<>")=0,"none",'
                f"SUMIFS({rng(col[field])},{crit}))"
            ))
        yoy.cell(row=i, column=7, value=f'=IF(OR(E{i}="none",F{i}="none"),"changed",F{i}-E{i})')
        yoy.cell(row=i, column=8, value=(
            f'=IF(OR(E{i}="none",F{i}="none"),"",IF(E{i}=0,"",F{i}/E{i}-1))'
        ))
        fmt = {"money": "£#,##0.00;-£#,##0.00;-", "pct": "0%", "int": "0;-0;-"}[kind]
        for c in (5, 6, 7):
            yoy.cell(row=i, column=c).number_format = fmt
        yoy.cell(row=i, column=8).number_format = "0.0%;-0.0%;-"
        for c in range(1, 9):
            yoy.cell(row=i, column=c).font = font(size=10)
            yoy.cell(row=i, column=c).border = BOX
    note_row = len(measures) + 3
    yoy.cell(row=note_row, column=1, value=(
        '"none" = no value in that year. From 6 April 2026 SSP has no lower earnings limit '
        "and no waiting days (Employment Rights Act 2025)."
    )).font = font(italic=True, size=9, color="595959")
    for letter, width in zip("ABCDEFGH", (32, 9, 17, 28, 12, 12, 12, 10), strict=True):
        yoy.column_dimensions[letter].width = width

    # ------------------------------------------------------------- Checks --
    chk = wb.create_sheet("Checks")
    header(chk, 1, [
        "Rates row", "Scheme", "Rate period", "From", "To", "Required fields",
        "Dates in order", "No overlap", "Next year joins on", "Rule has its inputs",
        "Weeks in order", "Row result",
    ])
    B, C, F, G = col["scheme"], col["rate_period"], col["effective_from"], col["effective_to"]
    H, I, J = col["awe_percentage"], col["weekly_flat_rate"], col["rate_rule"]
    D, E = col["period_start_week"], col["period_end_week"]
    for i in range(2, LAST + 1):
        r = i  # same row number as on Rates
        live = f"Rates!$A{r}<>\"\""
        chk.cell(row=i, column=1, value=f'=IF({live},{r},"")')
        chk.cell(row=i, column=2, value=f'=IF({live},Rates!${B}{r},"")')
        chk.cell(row=i, column=3, value=f'=IF({live},Rates!${C}{r},"")')
        chk.cell(row=i, column=4, value=f'=IF({live},Rates!${F}{r},"")')
        chk.cell(row=i, column=5, value=f'=IF({live},Rates!${G}{r},"")')
        required = " ,".join(
            f'Rates!${col[name]}{r}<>""'
            for name in ("tax_year", "scheme", "rate_period", "effective_from", "effective_to",
                         "rate_rule", "max_entitlement_weeks", "rounding", "source_reference",
                         "source_url")
        ).replace(" ,", ",")
        chk.cell(row=i, column=6, value=f'=IF({live},IF(AND({required}),"PASS","FAIL"),"")')
        chk.cell(row=i, column=7, value=f'=IF({live},IF(Rates!${G}{r}>=Rates!${F}{r},"PASS","FAIL"),"")')
        chk.cell(row=i, column=8, value=(
            f'=IF({live},IF(COUNTIFS({rng(B)},Rates!${B}{r},{rng(C)},Rates!${C}{r},'
            f'{rng(F)},"<="&Rates!${G}{r},{rng(G)},">="&Rates!${F}{r})=1,"PASS","FAIL"),"")'
        ))
        chk.cell(row=i, column=9, value=(
            f'=IF({live},IF(COUNTIFS({rng(B)},Rates!${B}{r},{rng(C)},Rates!${C}{r},'
            f'{rng(F)},">"&Rates!${G}{r})=0,"PASS (latest)",'
            f'IF(COUNTIFS({rng(B)},Rates!${B}{r},{rng(C)},Rates!${C}{r},'
            f'{rng(F)},Rates!${G}{r}+1)=1,"PASS","FAIL")),"")'
        ))
        chk.cell(row=i, column=10, value=(
            f'=IF({live},IF(OR(AND(Rates!${J}{r}="flat_rate_only",Rates!${I}{r}<>""),'
            f'AND(Rates!${J}{r}="percentage_only",Rates!${H}{r}<>""),'
            f'AND(Rates!${J}{r}="lower_of_flat_and_percentage",Rates!${H}{r}<>"",Rates!${I}{r}<>"")),'
            '"PASS","FAIL"),"")'
        ))
        chk.cell(row=i, column=11, value=f'=IF({live},IF(Rates!${E}{r}>=Rates!${D}{r},"PASS","FAIL"),"")')
        chk.cell(row=i, column=12, value=(
            f'=IF({live},IF(COUNTIF(F{i}:K{i},"FAIL*")=0,"PASS","FAIL"),"")'
        ))
        for c in range(1, 13):
            chk.cell(row=i, column=c).font = font(size=10)
        chk[f"D{i}"].number_format = chk[f"E{i}"].number_format = "yyyy-mm-dd"
    summary_row = LAST + 2
    chk.cell(row=summary_row, column=1, value="Overall").font = font(bold=True)
    chk.cell(row=summary_row, column=12, value=(
        f'=IF(COUNTIF(L2:L{LAST},"FAIL")=0,"ALL PASS",COUNTIF(L2:L{LAST},"FAIL")&" row(s) FAIL")'
    )).font = font(bold=True)
    chk["N1"] = "Overall result"
    chk["N1"].font = font(bold=True)
    chk["N2"] = f"=L{summary_row}"
    chk["N2"].font = font(bold=True, size=12)
    for rule_range in (f"F2:L{LAST}", "N2"):
        chk.conditional_formatting.add(
            rule_range, CellIsRule(operator="equal", formula=['"FAIL"'], fill=FAIL_FILL)
        )
        chk.conditional_formatting.add(
            rule_range, CellIsRule(operator="equal", formula=['"PASS"'], fill=PASS_FILL)
        )
    chk.conditional_formatting.add(
        "N2", CellIsRule(operator="equal", formula=['"ALL PASS"'], fill=PASS_FILL)
    )
    for letter, width in zip("ABCDEFGHIJKLMN", (9, 8, 16, 11, 11, 14, 13, 11, 17, 17, 14, 11, 2, 16), strict=True):
        chk.column_dimensions[letter].width = width
    chk.freeze_panes = "A2"

    for sheet in wb.worksheets:
        sheet.sheet_view.showGridLines = sheet.title in {"Rates", "Checks"}
    wb.save(OUT_PATH)
    print(f"wrote {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    build()

// Power Query (M) for the "StatutoryRates" table - SNOV-442.
//
// Create two text parameters in Power BI Desktop (Home > Transform data >
// Manage parameters) before pasting this into a Blank Query:
//   SourceMode           "csv" or "postgres"
//   StatutoryRatesCsv    full path to backend/app/reference_data/statutory_payment_rates.csv
// For "postgres" also create PgServer and PgDatabase. The connection needs read
// access to statutory_payment_rates only; it holds no personal data.
let
    FromCsv = () =>
        let
            Raw = Csv.Document(
                File.Contents(StatutoryRatesCsv),
                [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
            ),
            Promoted = Table.PromoteHeaders(Raw, [PromoteAllScalars = true])
        in
            Promoted,
    FromPostgres = () =>
        PostgreSQL.Database(
            PgServer,
            PgDatabase,
            [Query = "SELECT tax_year, scheme, rate_period, period_start_week, period_end_week, effective_from, effective_to, awe_percentage, weekly_flat_rate, rate_rule, lower_earnings_limit_weekly, relevant_period_weeks, qualifying_week_offset_weeks, continuous_employment_weeks, waiting_days, max_entitlement_weeks, payment_window_weeks, rounding, source_reference, source_url FROM statutory_payment_rates"]
        ),
    Source = if SourceMode = "postgres" then FromPostgres() else FromCsv(),
    // Empty CSV cells mean "not applicable" (e.g. SSP has no LEL from 2026/27)
    Nulled = Table.ReplaceValue(Source, "", null, Replacer.ReplaceValue,
        {"awe_percentage", "weekly_flat_rate", "lower_earnings_limit_weekly",
         "qualifying_week_offset_weeks", "continuous_employment_weeks", "payment_window_weeks",
         "effective_to"}),
    Typed = Table.TransformColumnTypes(
        Nulled,
        {
            {"tax_year", Int64.Type}, {"scheme", type text}, {"rate_period", type text},
            {"period_start_week", Int64.Type}, {"period_end_week", Int64.Type},
            {"effective_from", type date}, {"effective_to", type date},
            {"awe_percentage", type number}, {"weekly_flat_rate", Currency.Type},
            {"rate_rule", type text}, {"lower_earnings_limit_weekly", Currency.Type},
            {"relevant_period_weeks", Int64.Type}, {"qualifying_week_offset_weeks", Int64.Type},
            {"continuous_employment_weeks", Int64.Type}, {"waiting_days", Int64.Type},
            {"max_entitlement_weeks", Int64.Type}, {"payment_window_weeks", Int64.Type},
            {"rounding", type text}, {"source_reference", type text}, {"source_url", type text}
        },
        "en-GB"
    ),
    TaxYearLabel = Table.AddColumn(Typed, "tax_year_label",
        each Text.From([tax_year]) & "/" & Text.End(Text.From([tax_year] + 1), 2), type text),
    SchemePeriod = Table.AddColumn(TaxYearLabel, "scheme_period",
        each [scheme] & " - " & [rate_period], type text),
    HasEarningsTest = Table.AddColumn(SchemePeriod, "has_earnings_test",
        each [lower_earnings_limit_weekly] <> null, type logical)
in
    HasEarningsTest

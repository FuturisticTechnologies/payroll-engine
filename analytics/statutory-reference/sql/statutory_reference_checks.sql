-- Statutory payment reference data: analyst queries and data quality checks.
-- SNOV-442 · PostgreSQL · read-only. Run against any environment after the
-- 20261127_0008 migration. Every check query returns ZERO rows when healthy.

-- 1. What is in force on a given date (change the date) -----------------------
SELECT scheme, rate_period, tax_year, effective_from, effective_to,
       awe_percentage, weekly_flat_rate, rate_rule,
       lower_earnings_limit_weekly, waiting_days, max_entitlement_weeks,
       payment_window_weeks, source_url
FROM statutory_payment_rates
WHERE DATE '2026-06-01' BETWEEN effective_from AND COALESCE(effective_to, 'infinity'::date)
ORDER BY scheme, period_start_week;

-- 2. CHECK: overlapping rows for the same scheme and rate period --------------
-- (the exclusion constraint should make this impossible; this proves it)
SELECT a.scheme, a.rate_period, a.effective_from AS a_from, a.effective_to AS a_to,
       b.effective_from AS b_from, b.effective_to AS b_to
FROM statutory_payment_rates a
JOIN statutory_payment_rates b
  ON a.scheme = b.scheme AND a.rate_period = b.rate_period AND a.id < b.id
 AND daterange(a.effective_from, COALESCE(a.effective_to, 'infinity'::date), '[]')
  && daterange(b.effective_from, COALESCE(b.effective_to, 'infinity'::date), '[]');

-- 3. CHECK: gaps between consecutive tax years -------------------------------
SELECT scheme, rate_period, effective_to, next_from
FROM (
    SELECT scheme, rate_period, effective_to,
           LEAD(effective_from) OVER (PARTITION BY scheme, rate_period ORDER BY effective_from) AS next_from
    FROM statutory_payment_rates
) s
WHERE next_from IS NOT NULL AND next_from <> effective_to + 1;

-- 4. CHECK: a rule without the inputs it needs --------------------------------
SELECT scheme, rate_period, tax_year, rate_rule, awe_percentage, weekly_flat_rate
FROM statutory_payment_rates
WHERE (rate_rule = 'flat_rate_only' AND weekly_flat_rate IS NULL)
   OR (rate_rule = 'percentage_only' AND awe_percentage IS NULL)
   OR (rate_rule = 'lower_of_flat_and_percentage'
       AND (weekly_flat_rate IS NULL OR awe_percentage IS NULL));

-- 5. CHECK: rows with no source -----------------------------------------------
SELECT scheme, rate_period, tax_year
FROM statutory_payment_rates
WHERE COALESCE(source_reference, '') = '' OR source_url NOT LIKE 'https://www.gov.uk/%';

-- 6. CHECK: a scheme with nothing in force today (warns before a tax year ends)
SELECT s.scheme
FROM (VALUES ('SSP'), ('SMP'), ('SPP')) AS s(scheme)
WHERE NOT EXISTS (
    SELECT 1 FROM statutory_payment_rates r
    WHERE r.scheme = s.scheme
      AND CURRENT_DATE BETWEEN r.effective_from AND COALESCE(r.effective_to, 'infinity'::date)
);

-- 7. Year-on-year comparison (for the review pack) ----------------------------
SELECT cur.scheme, cur.rate_period, cur.tax_year,
       prev.weekly_flat_rate AS previous_flat_rate, cur.weekly_flat_rate AS flat_rate,
       cur.weekly_flat_rate - prev.weekly_flat_rate AS flat_rate_change,
       prev.lower_earnings_limit_weekly AS previous_lel, cur.lower_earnings_limit_weekly AS lel,
       prev.waiting_days AS previous_waiting_days, cur.waiting_days,
       prev.awe_percentage AS previous_awe_pct, cur.awe_percentage AS awe_pct
FROM statutory_payment_rates cur
LEFT JOIN statutory_payment_rates prev
  ON prev.scheme = cur.scheme AND prev.rate_period = cur.rate_period
 AND prev.tax_year = cur.tax_year - 1
ORDER BY cur.scheme, cur.period_start_week, cur.tax_year;

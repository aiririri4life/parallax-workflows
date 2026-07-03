# Phase 2 — Stress-test market assumptions (layers 1–4)

Loaded when Phase 2 fires, after the Assumption Map has been played back and corrected (Phase 1).
This phase produces the Pass-1 factual reads that Phase 5 (Pass 2, client conditioning) will later
re-weight but never overwrite.

## Market selection

Pick relevant markets per `_parallax/parallax-conventions.md` §6 (home market + revenue geography
+ commodity exposure + supply-chain dependency), **capped at 3**. If the thesis names no tickers,
derive markets from the thesis's own macro claims (e.g., a thesis about "US rate cuts" needs
`United States`; a thesis about "China reopening consumer demand" needs `China`).

Call `list_macro_countries` first if market coverage is in doubt — 15 markets, publicly-traded
equities only (see Known Limitations). A macro or sector claim about an uncovered market is marked
`out-of-scope` in the Assumption Map, not guessed.

## Batch — fire in parallel

For each selected market:

| Tool | Parameters | Use for |
|---|---|---|
| `get_telemetry` | `fields: ["regime_tag","signals","commentary.headline","commentary.mechanism","divergences"]` | Current regime baseline. **Async, ~15-30s** — do not block the rest of the batch on it. |
| `macro_analyst` | `market: "<market>"`, `component` per which layers the thesis needs: `"macro_indicators"` (inflation, growth, surprise-index reads — **fire this whenever the thesis makes an explicit inflation or Fed-path claim**, e.g. "disinflation continues" or "the Fed keeps cutting"), `"tactical"` (regime/rates/growth), `"factors"` (macro-level factor tilts), `"sectors"` (sector demand/pricing power claims), `"news"` (theme/sector-level news — **this is how theme news gets tested, not `get_news_synthesis`**, which is symbol-only and belongs to Phase 3) | Layer 1–4 assumption testing, one call per (market × component) |

Fire every (market × component) combination simultaneously — these are independent per
`_parallax/parallax-conventions.md` §3. A thesis touching 2 markets across 3 components is 6
parallel `macro_analyst` calls plus 2 `get_telemetry` calls, not a serial loop. **A CPI/inflation
or rate-path claim without a `macro_indicators` call is an Unconfirmed masquerading as a guess** —
don't classify A1/A2-style macro claims off `tactical` alone if the thesis's own wording turns on
the inflation trajectory specifically.

## Classification

For each layer-1–4 assumption in the Assumption Map, read the relevant `macro_analyst` /
`get_telemetry` output and classify:

- **Supported** — the current data points the same direction as the claim.
- **Contradicted** — the current data points the opposite direction.
- **Unconfirmed** — the data is silent, ambiguous, or the market is `out-of-scope`. **Never
  fabricate a read to force a Supported/Contradicted call** — Unconfirmed is a legitimate,
  frequent outcome and should be reported as such.

**Read staleness.** `macro_analyst` output carries its own `report_date`, which can lag `today`
(and lag `get_telemetry`'s date) by days to a couple of weeks. When the macro report materially
predates today, surface that `report_date` in **Confidence & Caveats** — the same staleness
discipline Phase 3 applies to news cards. A classification built on a two-week-old macro read is
still valid, but the reader must be able to see how old the signal behind it is.

## The stress step

For every assumption classified Supported or Contradicted (Unconfirmed assumptions have no break
condition to state — there's nothing confirmed to break), state:

1. **The adverse condition** that would flip Supported → false, in plain language (e.g., "the Fed
   holds rates through year-end instead of cutting").
2. **Magnitude** — how far the break condition would need to move the world (a 25bp surprise vs.
   a full regime reversal are different severities). Use the `macro_analyst` / `get_telemetry`
   data itself to calibrate this, not a generic guess.
3. **Time-to-play-out** — over what horizon the break condition would plausibly resolve (weeks,
   quarters, multi-year). **Both magnitude and time-to-play-out are required fields** — Phase 5
   cannot re-weight severity for a specific investor without them (time-to-play-out is compared
   against the client's horizon; magnitude is compared against their risk capacity).
4. **Base severity** — the client-invariant severity if this break condition fires: how much of
   the thesis's conclusion it takes down. This is the number Phase 5 re-weights; it is never
   itself a function of who holds the position.

## Output shape carried forward

Each layer-1–4 assumption exits Phase 2 with: `status` (Supported/Contradicted/Unconfirmed),
`break_condition` (text), `magnitude` (text + rough scale), `time_to_play_out` (text + rough
scale), `base_severity` (high/med/low). This record is what Phase 4 synthesizes and what Phase 5
re-weights — keep it structured, don't let it collapse into prose before Phase 4.

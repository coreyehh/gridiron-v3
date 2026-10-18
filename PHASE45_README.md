# Phase45 — Historical role / expected-starter reliability gate

Phase45 is a **risk gate, not a certified starting lineup feed**. It audits the already-frozen 12-fixture / 347-player Week6 Phase43 forecast snapshot. For each player it reads historical nflverse box appearances and share of team dropback/pass attempts, rush attempts or targets. It flags player rows missing from earlier source boxes **as unknown, never verified inactive**. It flags unstable opportunity shares, low QB share, and competing QB candidates on the same fixture team. It does not change original frozen projections.

Run [Phase45 Actions](https://github.com/coreyehh/gridiron-v3/actions/workflows/phase45-role-reliability.yml), select main and click Run workflow. The artifact is a spreadsheet-friendly, **public-safe CSV**, and a JSON summary. The workflow has **zero Odds API requests and zero qualified bets**.

The audit intentionally excludes **all 2026 Week6 or later rows**, even if they are now in a downloaded data file. The underlying nflverse source publication timing is not independently proven, so historical features are research evidence rather than an independently verified point-in-time injury/inactive record.

It never infers official game-day active status, expected starter, injury clearance, depth chart, passing role, touchdown probability calibration, EV or wager confidence from a roster file or missing prior box stat.

Next development is a source-authenticated official injury + inactive + depth chart layer and independent out-of-sample role/TD calibration, frozen for a future slate. Avoid retroactively upgrading historical Week6 bets with new data.

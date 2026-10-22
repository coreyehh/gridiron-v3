# Phase 47 — Historical odds ingestion and pregame validation

Status: validation component implemented; historical odds feed **not connected**. No verified EV claims.

Run from repository root:

```bash
python -m unittest discover -s tests -p 'test_phase47_validate_odds.py'
python scripts/phase47_validate_odds.py --input path/to/quotes.csv --accepted data/odds/accepted.jsonl --rejected data/odds/rejected.json
```

Input CSV fields: `player_id,season,week,market,direction,line,american_odds,quoted_at_utc,kickoff_utc,sportsbook`.
Use ISO-8601 timezone-aware timestamps. All quotes must precede kickoff and be within 24 hours of kickoff by default. Rejected records are quarantined with reasons. A nonzero exit code means at least one quote failed validation.

**Remaining before Phase 47 completion:** obtain a licensed or otherwise permissible historical player-prop odds feed, verify player IDs and game IDs, preserve source provenance and immutable raw snapshots, deduplicate by quote identity, test chronological pregame joins, and test the full pipeline on real source rows. Do not substitute current prices for historical prices.

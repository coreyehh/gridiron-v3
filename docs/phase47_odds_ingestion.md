# Phase 47 — Historical odds ingestion

**Implementation:** historical event-odds JSON normalization, explicit identity mapping, event kickoff verification, pregame validation, duplicate suppression within snapshot, raw SHA-256 provenance, rejection quarantine. **Integration remains blocked** until authenticated historical odds snapshots and verified event/player mapping are supplied. No real historical data was imported and no EV has been certified.

Provider: [The Odds API historical event odds](https://the-odds-api.com/historical-odds-data/), paid historical player-prop access. Historical event-odds endpoint returns a timestamped snapshot for one event; save original JSON unmodified and securely, outside public GitHub.

Required inputs:
- `--raw`: provider historical event-odds JSON with `timestamp` and `data.id`
- `--identities`: CSV columns `event_id,player_name,player_id`, verified rather than guessed
- `--schedules`: JSON map from provider event ID to `season,week,kickoff_utc` from verified schedule
- `--accepted`, `--rejected`: output paths

Run: `python scripts/phase47_provider.py --raw odds.json --identities identities.csv --schedules schedules.json --accepted accepted.jsonl --rejected rejected.json`

Run tests: `python -m unittest discover -s tests -p 'test_phase47_provider.py'`.

Safety: never commit keys, licensed odds payloads, or private wagering records. This script reads saved files and does not contact the provider. It uses the provider snapshot timestamp as quote time, rejects stale or post-kickoff snapshots, and refuses unresolved player IDs. It records SHA-256 of raw bytes for provenance but does not itself provide durable immutable storage. Quote deduplication is within one snapshot, not across multiple ingestions.

Remaining before full Phase 47 signoff: secure provider access; fetch and preserve real snapshots; verified event/player mapping; cross-file deduplication and immutable storage; integration test on actual licensed data; verify market coverage and time conventions.

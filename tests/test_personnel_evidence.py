import pandas as pd
import pytest
from matchup_engine.personnel_evidence import audit_personnel_evidence

def row(observed_at="2026-10-30T12:00:00Z",source="team injury report"):
    return pd.DataFrame([dict(game_id="g",team="CIN",points_adjustment=-3,
      source=source,observed_at=observed_at,reason="QB inactive")])

def test_fresh_evidence():
    result=audit_personnel_evidence(row(),"2026-10-31T00:00:00Z")
    assert result.evidence_age_hours.iloc[0]==12

def test_reject_stale_evidence():
    with pytest.raises(ValueError,match="Stale"):
        audit_personnel_evidence(row("2026-10-01T00:00:00Z"),"2026-10-31T00:00:00Z")

def test_reject_empty_source():
    with pytest.raises(ValueError,match="Blank"):
        audit_personnel_evidence(row(source=" "),"2026-10-31T00:00:00Z")

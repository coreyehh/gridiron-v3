"""Trusted availability source interface, intentionally without live provider.

Trust must come from a verifier controlled by the application, not JSON input.
A provider integration must authenticate origin, integrity, timestamp, and
the source record before issuing a positive attestation.
"""
from dataclasses import dataclass
from datetime import datetime,timezone
from typing import Protocol

@dataclass(frozen=True)
class Attestation:
    fixture_id:str
    player_id:str
    team:str
    source_record_id:str
    observed_at_utc:str
    source_name:str
    authenticated:bool

class AvailabilityVerifier(Protocol):
    def attest(self, *, evidence:dict, asof_utc:datetime)->Attestation|None: ...

class DenyAllVerifier:
    """Safe default while no authenticated provider is configured."""
    def attest(self, *, evidence:dict, asof_utc:datetime)->None:
        return None

def verify_attestation(verifier, evidence, asof_utc):
    if asof_utc.tzinfo is None:raise ValueError("Timezone-aware lock required")
    att=verifier.attest(evidence=evidence,asof_utc=asof_utc)
    if not isinstance(att,Attestation) or not att.authenticated:
        return False
    if not all((att.fixture_id,att.player_id,att.team,att.source_record_id,att.source_name)):
        return False
    try:
        observed=datetime.fromisoformat(att.observed_at_utc.replace("Z","+00:00"))
    except (ValueError,TypeError,AttributeError):
        return False
    if observed.tzinfo is None or observed.astimezone(timezone.utc)>asof_utc.astimezone(timezone.utc):
        return False
    return (str(evidence.get("fixture_id"))==att.fixture_id
        and str(evidence.get("player_id"))==att.player_id
        and str(evidence.get("team"))==att.team
        and str(evidence.get("source_record_id"))==att.source_record_id
        and str(evidence.get("source"))==att.source_name)

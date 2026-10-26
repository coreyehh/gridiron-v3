"""GRIDIRON wager approval boundary: all preconditions must be explicit.

A forecast is not a wager. No current production provider supplies these
attestations; therefore the default result is NO_BET.
"""
from datetime import datetime,timezone
from math import isfinite

def decide(candidate, *, asof_utc):
    if asof_utc.tzinfo is None:raise ValueError("Timezone-aware asof required")
    reasons=[]
    required=("fixture_id","player_id","market","selection","book","line",
              "decimal_odds","model_probability","market_observed_at_utc")
    if any(candidate.get(k) is None for k in required):
        reasons.append("INCOMPLETE_CANDIDATE")
    if candidate.get("official_active_verified") is not True:
        reasons.append("ACTIVE_STATUS_UNVERIFIED")
    if candidate.get("role_verified") is not True:
        reasons.append("ROLE_UNVERIFIED")
    if candidate.get("opponent_adjusted") is not True:
        reasons.append("OPPONENT_ADJUSTMENT_UNVERIFIED")
    if candidate.get("probabilities_calibrated") is not True:
        reasons.append("PROBABILITY_CALIBRATION_UNVERIFIED")
    if candidate.get("price_source_authenticated") is not True:
        reasons.append("SPORTSBOOK_PRICE_UNVERIFIED")
    if candidate.get("fixture_not_started_verified") is not True:
        reasons.append("KICKOFF_GATE_UNVERIFIED")
    try:
        ts=datetime.fromisoformat(str(candidate["market_observed_at_utc"]).replace("Z","+00:00"))
        if ts.tzinfo is None or ts.astimezone(timezone.utc)>asof_utc.astimezone(timezone.utc):
            reasons.append("INVALID_MARKET_ASOF")
    except (ValueError,KeyError,TypeError):
        reasons.append("INVALID_MARKET_ASOF")
    try:
        odds=float(candidate["decimal_odds"])
        prob=float(candidate["model_probability"])
        if not (isfinite(odds) and odds>1 and isfinite(prob) and 0<prob<1):
            reasons.append("INVALID_PRICE_OR_PROBABILITY")
    except (KeyError,TypeError,ValueError):
        reasons.append("INVALID_PRICE_OR_PROBABILITY")
        odds=prob=None
    edge=round(prob*odds-1,6) if odds is not None and prob is not None and isfinite(odds) and isfinite(prob) else None
    if edge is not None and edge<=0:reasons.append("NON_POSITIVE_EXPECTED_VALUE")
    # Explicit authorization is separate from a computed positive EV.
    if candidate.get("human_approved") is not True:
        reasons.append("NOT_APPROVED_FOR_WAGER")
    return {"status":"NO_BET" if reasons else "ELIGIBLE_FOR_HUMAN_REVIEW",
            "reasons":sorted(set(reasons)),"estimated_ev_per_unit":edge,
            "approved_units":0,"wager_submitted":False}

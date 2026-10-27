"""Audit roster and forecast coverage of an existing Phase43 snapshot.

This is a quality gate, not an official active-roster certification.
"""
from collections import Counter
from scripts.phase43_multimarket_forecasts import verify

def audit(snapshot):
    verify(snapshot)
    fixtures={f["id"]:f for f in snapshot["fixtures"]}
    issues=[]
    seen=set()
    weeks=Counter()
    for r in snapshot["forecasts"]:
        key=(r["fixture_id"],r["player_id"])
        if key in seen:issues.append({"type":"DUPLICATE_PLAYER_FIXTURE","key":list(key)})
        seen.add(key)
        fixture=fixtures[r["fixture_id"]]
        if r["team"] not in (fixture["home"],fixture["away"]):
            issues.append({"type":"TEAM_OUTSIDE_FIXTURE","fixture_id":r["fixture_id"],
                           "player_id":r["player_id"],"team":r["team"]})
        if r.get("active_verified") is not True:
            issues.append({"type":"ACTIVE_STATUS_UNVERIFIED","fixture_id":r["fixture_id"],
                           "player_id":r["player_id"]})
        if r.get("role_verified") is not True:
            issues.append({"type":"ROLE_UNVERIFIED","fixture_id":r["fixture_id"],
                           "player_id":r["player_id"]})
        last=(r.get("last_observed_season"),r.get("last_observed_week"))
        weeks[str(last)]+=1
        try:
            period=r["fixture_id"].split("-W",1)
            fixture_season=int(period[0])
            fixture_week=int(period[1].split("-",1)[0])
            if last[0] is None or last[1] is None:
                issues.append({"type":"MISSING_OBSERVATION_PERIOD","player_id":r["player_id"]})
            elif int(last[0])<fixture_season or (int(last[0])==fixture_season and fixture_week-int(last[1])>2):
                issues.append({"type":"STALE_PLAYER_USAGE","player_id":r["player_id"],
                               "last_observed_season":last[0],"last_observed_week":last[1]})
        except (ValueError,TypeError,IndexError):
            issues.append({"type":"INVALID_FIXTURE_PERIOD","player_id":r["player_id"]})

        if not r.get("player_name"):
            issues.append({"type":"MISSING_PLAYER_NAME","fixture_id":r["fixture_id"],
                           "player_id":r["player_id"]})
    return {"snapshot_sha256":snapshot["payload_sha256"],
            "forecast_players":len(snapshot["forecasts"]),
            "fixture_count":len(fixtures),
            "last_observed_periods":dict(weeks),
            "issue_counts":dict(Counter(x["type"] for x in issues)),
            "issues":issues,
            "current_roster_certified":False,
            "ready_for_wager_approval":False}

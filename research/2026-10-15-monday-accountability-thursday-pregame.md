# GRIDIRON accountability / candidate ledger — 2026-10-15

## Monday October 12: Buffalo Bills @ Los Angeles Rams (FINAL BUF 37, LA 34 OT)

**Source:** https://www.pro-football-reference.com/boxscores/202610120ram.htm

Previous public assistant research selections (not Phase 19 qualified bets and no model-derived price probabilities):

| Candidate | Earlier cited line | Actual result | Grade |
|---|---:|---:|---|
| Puka Nacua OVER 92.5 receiving yards | 92.5 | 138 receiving yards (17 catches, 24 targets) | WIN |
| Kyren Williams OVER 20.5 receiving yards | 20.5 | 27 receiving yards (6 catches, 8 targets) | WIN |
| Dalton Kincaid OVER 3.5 receptions | 3.5 | 1 reception (2 targets) | LOSS |

**Research-card hit rate:** 2 wins / 3 candidates (66.7%). Do **not** add to official GRIDIRON trained-model ROI or bet record. No standardized recorded stakes, verified execution timestamp/price, model win probabilities, or closing-line values for all candidates.

**Process diagnosis:** 71 points and overtime benefited Rams receiving overs, but BUF threw only 19 passes while Stafford attempted 54. The total alone cannot predict team-specific attempt/target distributions. Nacua's share of Rams targets was 24/54; Kyren's 8/54, whereas Kincaid had 2 of BUF's 19 attempts. Distinguish game total, team possessions, team dropbacks, target concentration, and pass efficiency. Do not double-count score-driven volume, fourth-quarter pushes, or overtime as repeatable baseline signals.

## Thursday October 15: Seattle Seahawks at Denver Broncos (PREGAME RESEARCH)

Sources: https://www.reuters.com/sports/seahawks-drake-thomas-broncos-pat-surtain-ii-out-thursday-game--flm-2026-10-15/ ;
https://dknetwork.draftkings.com/2026/10/15/best-bo-nix-prop-bet-for-broncos-vs-seahawks-on-thursday-10-15-26/ ;
https://dknetwork.draftkings.com/2026/10/15/best-emanuel-wilson-prop-bet-for-seahawks-at-broncos-on-thursday-10-14-26/ ;
https://edgelabs.bet/nfl/props

Market snapshot: Seattle -2.5; total ~40.5 DK. Sources are published sportsbook snapshots and not confirmed bets/real-time prices.

| Priority | Football candidate | Quoted reference threshold | Rationale | Main invalidation |
|---|---|---|---|---|
| 1 | Bo Nix UNDER passing yards | DraftKings 199.5 (-112) reported Oct 15 | Current-season 188.4 YPG; two of five above 200; Seattle pressure/run-fit defensive profile; lower projected total | Denver trailing substantially forces extreme attempts; short-field explosive completions |
| 2 | Emanuel Wilson OVER rush attempts | 17.5 threshold in contemporaneous published Oct 15 market commentary, price unverified | 21 and 20 carries previous two games, 79% Seahawks RB attempts while backfield depleted | Early deficit, snap-share reduction, unexpected active-status change |
| 3 | Jaxon Smith-Njigba OVER receiving yards | 92.5 at most books (line varies) | Surtain II and Hufanga ruled out; volume centerpiece; 2026 average above 100 YPG | Market already heavily prices his role, Darnold pressure, low scoring environment |

**Category:** unqualified research leans, **NOT** phase19-model probabilities or approved stakes. Book prices (especially Wilson attempts) require point-in-time verification before any recommendation. All 3 legs correlated with game state in various ways; **do not stack into a same-game parlay** based solely on individual leans. Official game-day actives must be checked shortly before kickoff.

## Required new modeling gates

1. **Game environment decomposition:** Independently forecast possessions × plays/drive × dropback rate × targets/dropback (by player). Account for offensive vs defensive possessions and overtime separately. Prior team totals without volume model are insufficient.
2. **Role and personnel:** Participation, routes run, targets per route, carry share, red-zone carries, competing eligible teammates, offensive line continuity, actives; measured confidence and missing-data.
3. **Price and outcome:** Calibrate distributions around offered *real* book lines, account for pushes/juice, compute no-vig fair probabilities, EV and confidence/shrinkage. No wager where these unavailable.
4. **Contrarian/under discipline:** Rank overs AND unders using the same outcome-first and risk gates. Differentiate median outcome from tail opportunity.
5. **Prospective honest logging:** Save immutable pregame model points, published sportsbook price, timestamp, injuries, qualitative football candidate or official final pick flag. Grade official picks and informal leans **separately**. Note overtime/late-score variance explicitly.
6. **Delivery:** User-facing player × market × direction × projection × book line × probability/confidence × reason, directly in chat; no key/terminal/dashboard prerequisites.


"""Auditable probability/price arithmetic; not a calibrated forecasting model."""
import math

def price(decimal_odds,model_probability,*,stake=1.0):
    odds=float(decimal_odds);p=float(model_probability);s=float(stake)
    if not all(math.isfinite(x) for x in (odds,p,s)) or odds<=1 or not 0<=p<=1 or s<=0:
        raise ValueError("Invalid odds, probability or stake")
    fair_decimal=(1/p) if p>0 else None
    breakeven=1/odds
    return {"decimal_odds":odds,"model_probability":p,
            "break_even_probability":breakeven,
            "probability_edge":p-breakeven,
            "expected_roi":p*odds-1,
            "expected_profit":s*(p*odds-1),
            "fair_decimal_odds":fair_decimal,
            "stake":s,
            "probability_calibrated_by_module":False,
            "sportsbook_price_verified_by_module":False}

def american_to_decimal(american):
    a=int(american)
    if a==0 or -100<a<100:raise ValueError("Invalid American odds")
    return 1+a/100 if a>0 else 1+100/abs(a)

def two_leg_joint(p_a,p_b,p_b_given_a):
    a=float(p_a);b=float(p_b);conditional=float(p_b_given_a)
    if not all(math.isfinite(x) and 0<=x<=1 for x in (a,b,conditional)):
        raise ValueError("Invalid probability")
    joint=a*conditional
    if joint>min(a,b)+1e-12 or joint<max(0,a+b-1)-1e-12:
        raise ValueError("Conditional probability violates joint probability bounds")
    return {"joint_probability":joint,"independent_product":a*b,
            "correlation_adjustment":joint-a*b,
            "conditional_probability":conditional,
            "joint_probability_calibrated_by_module":False}

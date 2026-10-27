"""Fail-closed result provenance for historical forecast evaluation.

A caller-provided result_verified=True is not authentication. The default
verifier rejects every result until a trusted source adapter is installed.
"""
from typing import Protocol

class ResultVerifier(Protocol):
    def verify(self, observation: dict) -> bool: ...

class DenyAllResultVerifier:
    def verify(self, observation: dict) -> bool:
        return False

def verify_results(observations, *, verifier=None):
    verifier=verifier or DenyAllResultVerifier()
    verified=[]
    for row in observations:
        if not isinstance(row,dict):
            raise ValueError("Malformed observed result")
        if row.get("result_verified") is not True:
            raise ValueError("Unverified observed result")
        if not row.get("source_record_id") or not row.get("source_name"):
            raise ValueError("Missing observed result source evidence")
        if verifier.verify(row) is not True:
            raise ValueError("Observed result source authentication failed")
        verified.append(dict(row))
    return verified

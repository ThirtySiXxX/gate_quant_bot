"""Independent, synthetic-only QR007 acceptance of an explicitly pinned producer.

No application/model imports, data discovery or fitting. `--prepare` never loads a
producer. Finance expectations are literals/Fraction identities, never QD helpers.
Socket blocking is a Python guard, not a sandbox for an arbitrary hostile module.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from contextlib import contextmanager
import copy
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import types

SCHEMA_COMMIT = "a183e40ed27b2250f7030ce3babbe5d579dc268b"
SCHEMA_SHA256 = "6e5fea553aedcdf6d800ced8a2ba5d0d49b5abd0b60cf931417fd6dff78408b7"
PROFILE = "qd007-synthetic-r2"
PENDING_CONTRACTS = ["B1: nullable current entry/exit fee attribution awaits owner schema/hash"]
NS = "qd007.synthetic-ledger"
BTC, ETH = "gate:usdt:BTC_USDT", "gate:usdt:ETH_USDT"
U = 1_000_000
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z", re.ASCII)
D_RE = re.compile(r"[+-]?(0|[1-9][0-9]*)(\.[0-9]+)?\Z", re.ASCII)
H_RE = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


class CheckError(ValueError):
    """An independent acceptance assertion failed."""


def demand(ok, message):
    if not ok:
        raise CheckError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def decimal_text(value):
    """Canonical exact decimal, independent of ambient Decimal context."""
    demand(type(value) is str and D_RE.fullmatch(value), "decimal string required")
    negative = value.startswith("-")
    text = value.lstrip("+-")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if Fraction(text) == 0:
        return "0"
    return ("-" if negative else "") + text


def money(value):
    demand(type(value) is str and decimal_text(value) == value, "noncanonical money")
    return Fraction(value)


def finite_decimal(value):
    """Exact rational -> terminating decimal for independent literal arithmetic."""
    value = Fraction(value)
    n, d = abs(value.numerator), value.denominator
    twos = fives = 0
    while d % 2 == 0:
        twos += 1; d //= 2
    while d % 5 == 0:
        fives += 1; d //= 5
    demand(d == 1, "oracle requires terminating decimal")
    scale = max(twos, fives)
    digits = str(n * 2 ** (scale-twos) * 5 ** (scale-fives)).zfill(scale+1)
    text = digits if not scale else digits[:-scale] + "." + digits[-scale:]
    return decimal_text(("-" if value < 0 else "") + text)


def independent_content(record):
    return digest({k: v for k, v in record.items() if k not in ("created_at_us", "source_refs")})


def fields(names, kind):
    return dict.fromkeys(names.split(), kind)


KEY = {**fields("record_id", "ID"), "instrument_id": "Inst",
       "record_type": "enum:Fill|FundingSnapshot|ObligationRevision|Posting|CompletenessAssertion|Valuation|Reserves",
       "revision": "I+"}
RANGE = {**fields("lot_id episode_id", "ID"), "unit_start": "I0", "unit_end": "I+"}
SHAPES = {
    "Key": KEY,
    "UnitRange": RANGE,
    "SourceRef": {"manifest_sha256": "H", "source_id": "ID", "source_row": "I+"},
    "Allocation": {**RANGE, "allocation_id": "H", "signed_cash_usdt": "D"},
    "ObligationRef": {"obligation_id": "ID", "revision": "I+"},
    "PostingRef": {"posting_id": "ID", "revision": "one"},
    "Scope": {"instrument_id": "Inst", **fields("trajectory_id episode_id", "ID"),
              "event_kinds": "list:enum:fill|fee|funding|posting",
              **fields("economic_from_us economic_to_exclusive_us", "T")},
    "LotState": {**fields("lot_id episode_id opening_fill_id", "ID"), "instrument_id": "Inst",
                 "opened_at_us": "T", "direction": "enum:long|short", "initial_contracts": "I+",
                 "remaining_contracts": "I0", **fields("entry_price multiplier", "D+"),
                 "live_ranges": "list:UnitRange", "closed_slice_ids": "list:ID"},
    "ClosedSlice": {**fields("slice_id lot_id episode_id closing_fill_id", "ID"), "closed_at_us": "T",
                    "unit_start": "I0", "unit_end": "I+",
                    **fields("realized_price_pnl_usdt entry_fee_cash_usdt exit_fee_cash_usdt", "D"),
                    "funding_cash_usdt": "?D", "attribution_revision": "I+", "null_reasons": "reasons"},
    "CoverageIssue": {"instrument_id": "Inst", "event_id": "ID",
                      "reason_code": "enum:MISSING_EXPECTED_SNAPSHOT|UNRESOLVED_SNAPSHOT_MAPPING"},
    "ObligationState": {**fields("obligation_id origin_id", "ID"), "instrument_id": "Inst",
                        "kind": "enum:fee|funding", "latest_revision": "?I+", "B_usdt": "D",
                        **fields("T_usdt P_usdt", "?D"), **fields("A_usdt L_usdt", "?D0"),
                        "allocation_refs": "list:H", "posting_refs": "list:Key", "null_reasons": "reasons"},
    "BalanceSnapshot": {**fields("as_of_us knowledge_cutoff_us", "T"), "view": "enum:as_known|restated",
                        "cash_usdt": "D", **fields("receivables_usdt liabilities_usdt reserved_margin_usdt reserved_fees_usdt", "?D0"),
                        **fields("unrealized_usdt economic_equity_usdt simulated_budget_usdt", "?D"),
                        "actual_available_margin_usdt": "null", **fields("new_risk_supported reductions_supported", "bool"),
                        **fields("valuation_refs reserve_refs", "list:ID"), "null_reasons": "reasons"},
    "Snapshot": {"namespace": "namespace", "schema_version": "one", "profile": "profile",
                 **fields("ledger_id trajectory_id scenario_id", "ID"), "view": "enum:as_known|restated",
                 **fields("as_of_us knowledge_cutoff_us", "T"), "causal_policy_sha256": "H",
                 "balances": "BalanceSnapshot", "lots": "list:LotState", "closed_slices": "list:ClosedSlice",
                 "obligations": "list:ObligationState", "coverage_issues": "list:CoverageIssue",
                 "null_reasons": "reasons", "state_sha256": "H"},
    "Readiness": {"episode_id": "ID", "as_of_us": "T", "natural_exit_at_us": "?T",
                  "status": "enum:open|immature|complete|invalid", "complete_at_us": "?T",
                  "assertion_refs": "list:Key", "blocking_reasons": "list:ID", "null_reasons": "reasons"},
    "LedgerEntry": {"entry_id": "H", "source_key": "Key", "transition": "enum:fee_claim|funding_claim|cash_posting|realized_pnl",
                    **fields("obligation_id episode_id", "?ID"), "allocation_id": "?H",
                    **fields("economic_at_us available_at_us", "T"), **fields("cash_delta_usdt realized_pnl_usdt", "D"),
                    **fields("pending_delta_usdt receivable_delta_usdt liability_delta_usdt", "?D"), "null_reasons": "reasons"},
    "Receipt": {"status": "enum:applied|duplicate", **fields("applied_keys duplicate_keys corroborated_keys", "list:Key"),
                "entries": "list:LedgerEntry", **fields("committed_before_sha256 committed_after_sha256", "H")},
    "FailureReceipt": {"code": "ID", "json_pointer": "str", "recoverable_identity": "?Key",
                       **fields("input_sha256 incumbent_sha256", "?H"), "committed_sha256": "H",
                       "disposition": "enum:reject|quarantine", "null_reasons": "reasons"},
    "Corroboration": {"key": "Key", "source_ref": "SourceRef"},
    "CommittedState": {"config": "object", "records": "list:Record", "derived_entries": "list:LedgerEntry",
                       "corroborating_source_refs": "list:Corroboration"},
    "Audit": {"namespace": "namespace", "schema_version": "one", "profile": "profile", "ledger_id": "ID",
              **fields("config_sha256 source_manifest_sha256 committed_sha256", "H"), "committed_state": "CommittedState",
              "integrity": "enum:clean|stopped", "failure_receipts": "list:FailureReceipt"},
}
COMMON = {"namespace": "namespace", "schema_version": "one", "record_type": KEY["record_type"],
          **fields("record_id trajectory_id scenario_id", "ID"), "revision": "I+", "instrument_id": "Inst",
          "evidence_mode": "enum:SCENARIO", **fields("created_at_us available_at_us", "T"),
          "source_time_precision": "enum:seconds|milliseconds|microseconds",
          "source_refs": "list:SourceRef", "null_reasons": "reasons"}
RECORDS = {
    "Fill": {**fields("order_id decision_id multiplier_rule_id fee_rule_id fee_obligation_id", "ID"),
             **fields("decision_at_us filled_at_us", "T"), "sequence": "?I+", "signed_contracts": "Q",
             **fields("fill_price multiplier", "D+"), "fee_fraction": "D", "liquidity_role": "enum:maker|taker|unknown",
             "role_basis": "enum:scenario", "fee_currency": "enum:USDT"},
    "FundingSnapshot": {"nominal_settlement_at_us": "?T", "snapshot_at_us": "T", "snapshot_sequence": "?I+",
                        "source_t_seconds": "?I", "source_record_at_us": "?T", "mapping_rule_id": "?ID",
                        "obligation_id": "ID", "eligible_ranges": "list:UnitRange"},
    "ObligationRevision": {"obligation_kind": "enum:fee|funding", **fields("origin_id authority_id rule_id", "ID"),
                           "supersedes_revision": "?I+", **fields("economic_at_us known_at_us", "T"),
                           "cumulative_signed_total_usdt": "?D", "allocations": "list:Allocation", "calculation": "?Calculation"},
    "Posting": {**fields("obligation_id booking_rule_id", "ID"), "signed_amount_usdt": "D",
                **fields("booking_at_us booking_known_at_us", "T"), "booking_basis": "enum:scenario",
                "corrects_posting_id": "?ID", "allocations": "list:Allocation"},
    "CompletenessAssertion": {"supersedes_revision": "?I+", "authority_id": "?ID", "finality_rule_id": "ID",
                              "scope": "Scope", "obligation_revision_refs": "list:ObligationRef",
                              "posting_refs": "list:PostingRef", **fields("asserted_at_us known_at_us", "T")},
    "Valuation": {**fields("valuation_at_us known_at_us", "T"), "price_kind": "enum:MARK", "mark_price": "?D+",
                  **fields("valuation_rule_id multiplier_rule_id", "ID")},
    "Reserves": {**fields("effective_at_us expires_at_us known_at_us", "T"),
                 **fields("reserved_margin_usdt reserved_fees_usdt", "?D0"),
                 "excludes_counted_losses_liabilities_and_posted_fees": "bool"},
}
REASONS = set("NOT_APPLICABLE UNKNOWN_RATE UNKNOWN_SOURCE_TIME UNKNOWN_MAPPING UNKNOWN_MARK UNKNOWN_AMOUNT UNKNOWN_BOOKING UNKNOWN_FINALITY UNKNOWN_SEQUENCE OPEN_ENDED_SCENARIO STALE_VALUATION UNKNOWN_RESERVES RESTATED_VIEW NOT_MODELED UNRESOLVED_DEPENDENCY UNKNOWN_OBLIGATION_TOTAL UNKNOWN_PRIOR_BALANCE UNKNOWN_CURRENT_BALANCE UNRESOLVED_SNAPSHOT_COVERAGE AGGREGATE_OBLIGATION OPEN_EPISODE UNSETTLED_OBLIGATION UNRESOLVED_FINALITY INVALID_ASSERTION_AUTHORITY UNKNOWN_INPUT_IDENTITY NONCANONICAL_INPUT NO_INCUMBENT".split())


def shape(kind, value, path="$", declaration=None):
    """Closed recursive field/type validation, including local null reasons."""
    if kind.startswith("?"):
        if value is None:
            return
        return shape(kind[1:], value, path)
    if kind.startswith("list:"):
        demand(type(value) is list, path + " expected list")
        for i, child in enumerate(value):
            shape(kind[5:], child, f"{path}/{i}")
        return
    if kind.startswith("enum:"):
        demand(type(value) is str and value in kind[5:].split("|"), path + " enum")
        return
    if kind == "Record":
        demand(type(value) is dict and value.get("record_type") in RECORDS, path + " record tag")
        return shape("fields", value, path, {**COMMON, **RECORDS[value["record_type"]]})
    if kind == "Calculation":
        demand(type(value) is dict, path + " calculation")
        decl = {"kind": "enum:authoritative_total"}
        if value.get("kind") == "funding_formula":
            decl = {"kind": "enum:funding_formula", "signed_contracts": "Q", **fields("multiplier mark_price", "D+"),
                    "final_rate": "D", **fields("valuation_at_us valuation_available_at_us rate_available_at_us", "T"),
                    **fields("valuation_rule_id multiplier_rule_id", "ID")}
        return shape("fields", value, path, decl)
    if kind in SHAPES or declaration is not None:
        decl = declaration if declaration is not None else SHAPES[kind]
        demand(type(value) is dict and set(value) == set(decl), path + " fields differ")
        for key, typ in decl.items():
            shape(typ, value[key], path + "/" + key)
        if "null_reasons" in decl:
            demand(set(value["null_reasons"]) == {k for k, v in value.items() if v is None}, path + " null reasons differ")
        return
    if kind in ("D", "D0", "D+"):
        v = money(value)
        demand(kind == "D" or (v >= 0 if kind == "D0" else v > 0), path + " decimal sign")
    elif kind in ("I", "I0", "I+", "Q", "T", "one"):
        demand(type(value) is int and -(2**63) <= value <= 2**63-1, path + " integer")
        if kind in ("I0", "T"): demand(value >= 0, path + " nonnegative")
        if kind == "I+": demand(value > 0, path + " positive")
        if kind == "Q": demand(value != 0 and value > -(2**63), path + " signed quantity")
        if kind == "one": demand(value == 1, path + " version")
    elif kind in ("ID", "H"):
        demand(type(value) is str and (ID_RE if kind == "ID" else H_RE).fullmatch(value), path + " identifier")
    elif kind == "Inst": demand(value in (BTC, ETH), path + " instrument")
    elif kind == "namespace": demand(value == NS, path + " namespace")
    elif kind == "profile": demand(value == PROFILE, path + " profile")
    elif kind == "bool": demand(type(value) is bool, path + " bool")
    elif kind == "null": demand(value is None, path + " null")
    elif kind == "str": demand(type(value) is str, path + " string")
    elif kind == "object": demand(type(value) is dict, path + " object")
    elif kind == "reasons":
        demand(type(value) is dict and all(type(k) is str and type(v) is str and v in REASONS for k, v in value.items()), path + " reasons")
    else: raise CheckError("unknown checker type " + kind)


def check_entry(entry):
    shape("LedgerEntry", entry)
    cash, pnl = money(entry["cash_delta_usdt"]), money(entry["realized_pnl_usdt"])
    transition = entry["transition"]
    if transition == "realized_pnl":
        demand(entry["obligation_id"] is None and entry["allocation_id"] is not None and entry["episode_id"] is not None, "realized entry owners")
        demand(cash == pnl and all(entry[k] == "0" for k in ("pending_delta_usdt", "receivable_delta_usdt", "liability_delta_usdt")), "realized entry effects")
    else:
        demand(entry["obligation_id"] is not None and entry["allocation_id"] is None and pnl == 0, "aggregate obligation entry")
        demand(entry["null_reasons"]["allocation_id"] == "AGGREGATE_OBLIGATION", "aggregate reason")
        demand(cash != 0 if transition == "cash_posting" else cash == 0, "claim/posting cash separation")
    p, a, l = (entry[k] for k in ("pending_delta_usdt", "receivable_delta_usdt", "liability_delta_usdt"))
    if all(v is not None for v in (p, a, l)):
        demand(money(p) == money(a)-money(l), "entry pending identity")
    for key in ("pending_delta_usdt", "receivable_delta_usdt", "liability_delta_usdt"):
        if entry[key] is None:
            demand(entry["null_reasons"][key] in {"UNKNOWN_PRIOR_BALANCE", "UNKNOWN_CURRENT_BALANCE", "UNKNOWN_OBLIGATION_TOTAL"}, "conditional delta reason")


def check_receipt(receipt):
    shape("Receipt", receipt)
    for entry in receipt["entries"]: check_entry(entry)
    demand(len({v["entry_id"] for v in receipt["entries"]}) == len(receipt["entries"]), "duplicate journal entry")


def check_audit(audit, config):
    shape("Audit", audit)
    state = audit["committed_state"]
    demand(state["config"] == config, "audit config differs from explicit fixture")
    demand(audit["config_sha256"] == digest(config), "config hash")
    demand(audit["source_manifest_sha256"] == digest(config["source_manifest"]), "manifest hash")
    demand(audit["committed_sha256"] == digest(state), "committed hash")
    rows = {(v["source_id"], v["source_row"]): v["payload_sha256"] for v in config["source_manifest"]["rows"]}
    for record in state["records"]:
        demand(record["source_refs"], "empty source provenance")
        for ref in record["source_refs"]:
            demand(ref["manifest_sha256"] == audit["source_manifest_sha256"] and rows[(ref["source_id"], ref["source_row"])] == independent_content(record), "audit source binding")
    for entry in state["derived_entries"]: check_entry(entry)
    records = {record_key(r):r for r in state["records"]}
    demand(len(records)==len(state["records"]),"duplicate accepted input identity")
    postings=Counter()
    realized={}
    for entry in state["derived_entries"]:
        key=record_key(entry["source_key"])
        demand(key in records,"journal source missing")
        source=records[key]
        if entry["transition"]=="cash_posting":
            demand(source["record_type"]=="Posting" and entry["obligation_id"]==source["obligation_id"]
                   and entry["cash_delta_usdt"]==source["signed_amount_usdt"],"cash entry differs from independent source")
            postings[key]+=1
        elif entry["transition"]=="realized_pnl":
            demand(source["record_type"]=="Fill","realized source type")
            realized.setdefault(key,[]).append(money(entry["realized_pnl_usdt"]))
        else:
            demand(source["record_type"] in {"Fill","ObligationRevision","FundingSnapshot"},"claim source type")
        demand(entry["available_at_us"]==source["available_at_us"],"journal consumer time differs")
    demand(postings==Counter({k:1 for k,r in records.items() if r["record_type"]=="Posting"}),"posting missing or double counted")
    oracle=reference_closures(list(records.values()))
    demand({k:Counter(v) for k,v in realized.items()}=={k:Counter(v) for k,v in oracle.items()},"realized journal differs from FIFO price oracle")


def record_key(record):
    return tuple(record[k] for k in ("instrument_id","record_type","record_id","revision"))


def reference_closures(records):
    """Small independent FIFO price oracle; no fee/funding implementation reuse."""
    inventory={}; result={}
    fills=sorted((r for r in records if r["record_type"]=="Fill"),
                 key=lambda r:(r["filled_at_us"],r["sequence"] or 0,r["instrument_id"],r["record_id"]))
    for fill in fills:
        lots=inventory.setdefault(fill["instrument_id"],[])
        q=fill["signed_contracts"];price=money(fill["fill_price"]);mult=money(fill["multiplier"])
        while lots and q*lots[0][0]<0:
            old,entry,m=lots[0];n=min(abs(q),abs(old));direction=1 if old>0 else -1
            demand(m==mult,"oracle refuses unproved multiplier conversion")
            result.setdefault(record_key(fill),[]).append(direction*n*m*(price-entry))
            lots[0][0]-=direction*n;q+=direction*n
            if lots[0][0]==0:lots.pop(0)
        if q:lots.append([q,price,mult])
    return result


def check_snapshot(snapshot, config, expected=None, quantities=None, records=None):
    shape("Snapshot", snapshot)
    demand(snapshot["state_sha256"] == digest({k: v for k, v in snapshot.items() if k != "state_sha256"}), "state hash")
    demand(snapshot["causal_policy_sha256"] == digest({k: v for k, v in config.items() if k != "source_manifest"}), "causal policy hash")
    for key in ("ledger_id", "trajectory_id", "scenario_id"): demand(snapshot[key] == config[key], "snapshot owner")
    b = snapshot["balances"]
    for key in ("as_of_us", "knowledge_cutoff_us", "view"): demand(b[key] == snapshot[key], "balance clock/view")
    ids = [o["obligation_id"] for o in snapshot["obligations"]]
    demand(len(ids) == len(set(ids)), "duplicate obligation output")
    for o in snapshot["obligations"]:
        if o["T_usdt"] is None:
            demand(all(o[k] is None for k in ("P_usdt", "A_usdt", "L_usdt")), "unknown obligation was zero-filled")
            for k in ("T_usdt", "P_usdt", "A_usdt", "L_usdt"):
                demand(o["null_reasons"][k] == "UNKNOWN_OBLIGATION_TOTAL", "unknown obligation reason")
        else:
            p = money(o["T_usdt"])-money(o["B_usdt"])
            demand((money(o["P_usdt"]), money(o["A_usdt"]), money(o["L_usdt"])) == (p, max(p, 0), max(-p, 0)), "T/B/P identity")
    unresolved = bool(snapshot["coverage_issues"]) or any(o["T_usdt"] is None for o in snapshot["obligations"])
    if unresolved:
        demand(all(b[k] is None for k in ("receivables_usdt", "liabilities_usdt", "economic_equity_usdt", "simulated_budget_usdt")), "unknown aggregate hidden")
        reason = "UNRESOLVED_SNAPSHOT_COVERAGE" if snapshot["coverage_issues"] else "UNKNOWN_OBLIGATION_TOTAL"
        demand(b["null_reasons"]["receivables_usdt"] == b["null_reasons"]["liabilities_usdt"] == reason, "unknown aggregate reason")
    else:
        for out, field in (("receivables_usdt", "A_usdt"), ("liabilities_usdt", "L_usdt")):
            demand(money(b[out]) == sum((money(o[field]) for o in snapshot["obligations"]), Fraction(0)), "separate aggregate " + out)
    if all(b[k] is not None for k in ("receivables_usdt", "liabilities_usdt", "unrealized_usdt")):
        e = money(b["cash_usdt"])+money(b["receivables_usdt"])-money(b["liabilities_usdt"])+money(b["unrealized_usdt"])
        demand(money(b["economic_equity_usdt"]) == e, "economic equity identity")
    if b["simulated_budget_usdt"] is not None:
        budget = money(b["cash_usdt"])-money(b["liabilities_usdt"])+min(money(b["unrealized_usdt"]), 0)-money(b["reserved_margin_usdt"])-money(b["reserved_fees_usdt"])
        demand(money(b["simulated_budget_usdt"]) == budget, "budget identity")
        demand(b["new_risk_supported"] == (budget > 0), "budget support flag")
    else: demand(b["new_risk_supported"] is False, "unknown budget must block risk")
    if snapshot["view"] == "restated":
        demand(b["simulated_budget_usdt"] is None and b["null_reasons"]["simulated_budget_usdt"] == "RESTATED_VIEW", "restated not decision budget")
    demand(b["null_reasons"]["actual_available_margin_usdt"] == "NOT_MODELED", "actual margin claim")
    if expected:
        for key, value in expected.items(): demand(b[key] == value, f"literal oracle {key}: {b[key]!r} != {value!r}")
    if quantities is not None:
        demand({v["lot_id"]: v["remaining_contracts"] for v in snapshot["lots"]} == quantities, "literal inventory")
    for lot in snapshot["lots"]:
        demand(sum(r["unit_end"]-r["unit_start"] for r in lot["live_ranges"]) == lot["remaining_contracts"], "live unit conservation")
        closed = [r for r in snapshot["closed_slices"] if r["lot_id"] == lot["lot_id"]]
        demand(sum(r["unit_end"]-r["unit_start"] for r in closed)+lot["remaining_contracts"] == lot["initial_contracts"], "closed unit conservation")
        demand(set(lot["closed_slice_ids"]) == {v["slice_id"] for v in closed}, "slice references")
    if records is not None:check_source_levels(snapshot,config,records)
    return snapshot


def check_source_levels(snapshot,config,records):
    """Independent source-to-level reconciliation, even after output rehashing."""
    e,k=snapshot["as_of_us"],snapshot["knowledge_cutoff_us"]
    visible=[r for r in records if r["available_at_us"]<=k]
    origins={}; totals={}; booked={}
    fills=[r for r in visible if r["record_type"]=="Fill" and r["filled_at_us"]<=e]
    for r in fills:
        name=r["fee_obligation_id"];origins[name]=r["instrument_id"]
        totals[name]=-abs(r["signed_contracts"])*money(r["multiplier"])*money(r["fill_price"])*money(r["fee_fraction"])
    for r in visible:
        if r["record_type"]=="FundingSnapshot" and r["snapshot_at_us"]<=e:
            name=r["obligation_id"];origins[name]=r["instrument_id"]
            if r["mapping_rule_id"] is not None:totals[name]=None if r["eligible_ranges"] else Fraction(0)
    revisions=sorted((r for r in visible if r["record_type"]=="ObligationRevision" and r["economic_at_us"]<=e),key=lambda r:(r["available_at_us"],r["revision"]))
    for r in revisions:
        if r["record_id"] in origins:
            totals[r["record_id"]]=None if r["cumulative_signed_total_usdt"] is None else money(r["cumulative_signed_total_usdt"])
    cash=money(config["initial_cash_usdt"])+sum((sum(v,Fraction(0)) for v in reference_closures(fills).values()),Fraction(0))
    for r in visible:
        if r["record_type"]=="Posting" and r["obligation_id"] in origins and (snapshot["view"]=="as_known" or r["booking_at_us"]<=e):
            amount=money(r["signed_amount_usdt"]);cash+=amount
            booked[r["obligation_id"]]=booked.get(r["obligation_id"],Fraction(0))+amount
    demand(money(snapshot["balances"]["cash_usdt"])==cash,"cash differs from source replay oracle")
    actual={r["obligation_id"]:r for r in snapshot["obligations"]}
    demand(set(totals)<=set(actual)<=set(origins),"unknown/missing source obligation identity")
    for name,t in totals.items():
        row=actual[name]
        demand(row["instrument_id"]==origins[name],"obligation source owner")
        demand(row["T_usdt"]==(None if t is None else finite_decimal(t)),"T differs from latest available source")
        demand(money(row["B_usdt"])==booked.get(name,Fraction(0)),"B differs from independent posting sources")


def balance(c, a, l, u, e, budget=None):
    return dict(cash_usdt=c, receivables_usdt=a, liabilities_usdt=l, unrealized_usdt=u,
                economic_equity_usdt=e, simulated_budget_usdt=budget)


def obligation(snapshot, name, **expected):
    found = [o for o in snapshot["obligations"] if o["obligation_id"] == name]
    demand(len(found) == 1, "missing/duplicate obligation " + name)
    for key, value in expected.items(): demand(found[0][key] == value, "obligation literal " + name + "/" + key)
    return found[0]


def check_readiness(value):
    shape("Readiness",value)
    status=value["status"];reasons=value["null_reasons"]
    if value["natural_exit_at_us"] is None:
        demand(reasons["natural_exit_at_us"]=="OPEN_EPISODE","natural exit null reason")
    else:
        demand(value["natural_exit_at_us"]<=value["as_of_us"],"future natural exit")
    if status=="complete":
        demand(value["natural_exit_at_us"] is not None and value["complete_at_us"] is not None
               and value["natural_exit_at_us"]<=value["complete_at_us"]<=value["as_of_us"]
               and not value["blocking_reasons"],"complete readiness conditions")
    else:
        demand(value["complete_at_us"] is None,"incomplete readiness has known completion")
        allowed={"open":{"OPEN_EPISODE"},"invalid":{"INVALID_ASSERTION_AUTHORITY"},
                 "immature":{"UNRESOLVED_SNAPSHOT_COVERAGE","UNKNOWN_OBLIGATION_TOTAL","UNSETTLED_OBLIGATION","UNRESOLVED_FINALITY"}}
        demand(reasons["complete_at_us"] in allowed[status],"readiness null reason inconsistent")
        if status=="open":demand(value["natural_exit_at_us"] is None,"open episode has natural exit")
    return value


class Fixture:
    """Input construction only. Does not compute expected ledger transitions."""
    def __init__(self, cash="10000", assets=(BTC,), fee="0.0005", multiplier="0.001", calendar=()):
        self.records = []
        self.fee, self.multiplier = fee, multiplier
        self.config = dict(namespace=NS, schema_version=1, ledger_id="qr007", trajectory_id="trajectory",
                           scenario_id="literal", instruments=sorted(assets), initial_at_us=0,
                           end_exclusive_us=1000*U, initial_cash_usdt=cash, allocation_quantum_usdt="0.0000000001",
                           rules=[], expected_funding_snapshots=[], source_manifest={})
        for inst in assets:
            params = {"fee": {"role": "taker", "signed_fraction": fee, "fee_currency": "USDT"},
                      "funding": {"calendar": "explicit_snapshot_list"},
                      "multiplier": {"base_per_contract": multiplier, "quantity_unit": "contracts"},
                      "valuation": {"price_kind": "MARK", "max_age_us": 60*U},
                      "sequence": {"same_time_order": "snapshot_before_fills"},
                      "booking": {"policy": "explicit_posting_records"},
                      "finality": {"policy": "explicit_scoped_assertions", "authority_id": "authority"}}
            for kind, parameters in params.items():
                self.config["rules"].append(dict(rule_id=self.rule(kind, inst), kind=kind, instrument_id=inst,
                    valid_from_us=0, valid_to_exclusive_us=1000*U, available_at_us=0, authority_id="authority", parameters=parameters, null_reasons={}))
        for inst, name, t in calendar:
            self.config["expected_funding_snapshots"].append(dict(instrument_id=inst, event_id=name, snapshot_at_us=t, mapping_rule_id=self.rule("funding", inst)))
        self.config["expected_funding_snapshots"].sort(key=lambda r:(r["instrument_id"], r["snapshot_at_us"], r["event_id"]))

    @staticmethod
    def rule(kind, inst=BTC): return inst.rsplit(":", 1)[1] + "-" + kind

    def add(self, kind, name, at, inst=BTC, revision=1, null_reasons=None, **extra):
        record = dict(namespace=NS, schema_version=1, record_type=kind, record_id=name, revision=revision,
                      instrument_id=inst, trajectory_id="trajectory", scenario_id="literal", evidence_mode="SCENARIO",
                      created_at_us=900*U, available_at_us=at, source_time_precision="microseconds", source_refs=[],
                      null_reasons={} if null_reasons is None else null_reasons, **extra)
        self.records.append(record)
        return record

    def fill(self, name, t, q, price, inst=BTC, available=None):
        return self.add("Fill", name, t if available is None else available, inst, order_id="order-"+name,
                        decision_id="decision-"+name, decision_at_us=max(0,t-1), filled_at_us=t, sequence=1,
                        signed_contracts=q, fill_price=price, multiplier=self.multiplier,
                        multiplier_rule_id=self.rule("multiplier",inst), fee_fraction=self.fee,
                        fee_rule_id=self.rule("fee",inst), liquidity_role="taker", role_basis="scenario",
                        fee_currency="USDT", fee_obligation_id="fee-"+name)

    @staticmethod
    def unit(opening, lo, hi):
        return dict(lot_id="lot:"+opening, episode_id="episode:"+opening, unit_start=lo, unit_end=hi)

    def alloc(self, name, ranges, inst=BTC):
        return [dict(r, signed_cash_usdt=amount, allocation_id=digest(["qr007", "trajectory", "literal", inst, name,
                    r["lot_id"], r["unit_start"], r["unit_end"]])) for r, amount in ranges]

    def snapshot(self, name, t, ranges, inst=BTC):
        return self.add("FundingSnapshot",name,t,inst,nominal_settlement_at_us=t,snapshot_at_us=t,
                        snapshot_sequence=None, source_t_seconds=t//U, source_record_at_us=t,
                        mapping_rule_id=self.rule("funding",inst), obligation_id="fund-"+name,eligible_ranges=ranges,
                        null_reasons={"snapshot_sequence":"UNKNOWN_SEQUENCE"})

    def revision(self, name, origin, economic, available, total, ranges, rev=1, kind="funding", inst=BTC, calculation=None):
        reasons = {"supersedes_revision":"NOT_APPLICABLE"} if rev == 1 else {}
        if total is None: reasons.update(cumulative_signed_total_usdt="UNKNOWN_AMOUNT", calculation="UNKNOWN_AMOUNT")
        return self.add("ObligationRevision",name,available,inst,revision=rev,obligation_kind=kind,origin_id=origin,
                        supersedes_revision=None if rev==1 else rev-1,authority_id="authority",rule_id=self.rule(kind,inst),
                        economic_at_us=economic,known_at_us=available,cumulative_signed_total_usdt=total,
                        allocations=self.alloc(name,ranges,inst) if total is not None else [],
                        calculation=None if total is None else calculation or {"kind":"authoritative_total"},null_reasons=reasons)

    def post(self, name, ob, t, total, ranges, inst=BTC, available=None, corrects=None):
        return self.add("Posting",name,t if available is None else available,inst,obligation_id=ob,signed_amount_usdt=total,
                        booking_at_us=t,booking_known_at_us=t if available is None else available,booking_basis="scenario",
                        booking_rule_id=self.rule("booking",inst),corrects_posting_id=corrects,allocations=self.alloc(ob,ranges,inst),
                        null_reasons={"corrects_posting_id":"NOT_APPLICABLE"} if corrects is None else {})

    def mark(self, name, t, price, inst=BTC):
        return self.add("Valuation",name,t,inst,valuation_at_us=t,known_at_us=t,price_kind="MARK",mark_price=price,
                        valuation_rule_id=self.rule("valuation",inst),multiplier_rule_id=self.rule("multiplier",inst),
                        null_reasons={"mark_price":"UNKNOWN_MARK"} if price is None else {})

    def reserve(self, inst=BTC, margin="0", fees="0"):
        return self.add("Reserves","reserve-"+inst.rsplit(":",1)[1],0,inst,effective_at_us=0,expires_at_us=1000*U,
                        known_at_us=0,reserved_margin_usdt=margin,reserved_fees_usdt=fees,
                        excludes_counted_losses_liabilities_and_posted_fees=True)

    def assertion(self, t, obrefs, posts, revision=1, authority="authority", end=3*U+1):
        reasons = {"supersedes_revision":"NOT_APPLICABLE"} if revision==1 else {}
        if authority is None: reasons["authority_id"]="UNKNOWN_FINALITY"
        return self.add("CompletenessAssertion","assert",t,revision=revision,supersedes_revision=None if revision==1 else revision-1,
            authority_id=authority,finality_rule_id=self.rule("finality"),scope=dict(instrument_id=BTC,trajectory_id="trajectory",
            episode_id="episode:o",event_kinds=sorted(["fill","fee","funding","posting"]),economic_from_us=U,economic_to_exclusive_us=end),
            obligation_revision_refs=sorted([dict(obligation_id=o,revision=r) for o,r in obrefs],key=canonical),
            posting_refs=sorted([dict(posting_id=p,revision=1) for p in posts],key=canonical),asserted_at_us=t,known_at_us=t,null_reasons=reasons)

    def seal(self):
        config, records = copy.deepcopy(self.config), copy.deepcopy(self.records)
        manifest = dict(namespace="qd007.synthetic-sources",schema_version=1,fixture_id="qr007-literals",
                        rows=[dict(source_id="literal",source_row=i,payload_sha256=independent_content(r)) for i,r in enumerate(records,1)])
        config["source_manifest"] = manifest
        mh = digest(manifest)
        for i, record in enumerate(records,1): record["source_refs"]=[dict(manifest_sha256=mh,source_id="literal",source_row=i)]
        return config, records


def apply_fixture(api, fixture, records=None):
    config, all_records = fixture.seal()
    submitted = all_records if records is None else [all_records[i] for i in records]
    before = copy.deepcopy((config,submitted))
    ledger = api.Ledger(config)
    receipt = ledger.apply_batch(submitted)
    check_receipt(receipt); check_audit(ledger.audit(), config)
    demand((config,submitted) == before, "producer mutated input")
    return CheckedLedger(ledger,config,submitted), config, all_records, receipt


class CheckedLedger:
    """Read-only test wrapper; never uses producer outputs as expected inputs."""
    def __init__(self,ledger,config,records):
        self._ledger=ledger;self._config=copy.deepcopy(config);self._records=copy.deepcopy(records)

    def snapshot(self,t):
        return check_snapshot(self._ledger.snapshot(t),self._config,records=self._records)

    def restated(self,t,k):
        return check_snapshot(self._ledger.restated(t,k),self._config,records=self._records)

    def readiness(self,episode,t):
        return check_readiness(self._ledger.readiness(episode,t))

    def __getattr__(self,name):return getattr(self._ledger,name)


CASES = []


def case(case_id, criteria, purpose):
    def register(fn):
        CASES.append((case_id, tuple(criteria.split()), purpose, fn))
        return fn
    return register


def rejected(api, fixture, code=None, prefix=()):
    config, records = fixture.seal()
    ledger = api.Ledger(config)
    if prefix: check_receipt(ledger.apply_batch([records[i] for i in prefix]))
    before = ledger.audit()
    check_audit(before,config)
    batch = [r for i,r in enumerate(records) if i not in prefix]
    try:
        ledger.apply_batch(batch)
    except api.LedgerError:
        pass
    else: raise CheckError("invalid fixture accepted")
    after=ledger.audit(); check_audit(after,config)
    demand(after["committed_state"]==before["committed_state"] and after["committed_sha256"]==before["committed_sha256"], "batch leaked committed prefix")
    demand(after["integrity"]=="stopped" and after["failure_receipts"], "missing integrity stop")
    if code: demand(after["failure_receipts"][-1]["code"]==code,"wrong rejection code")
    for invoke in (lambda:ledger.snapshot(10*U),lambda:ledger.apply_batch([]),lambda:ledger.readiness("episode:o",10*U)):
        try: invoke()
        except api.LedgerError as exc:
            error_code=getattr(exc,"code",None)
            if error_code is None and isinstance(getattr(exc,"receipt",None),dict): error_code=exc.receipt.get("code")
            demand(error_code=="INTEGRITY_STOPPED","stopped API error code")
        else: raise CheckError("stopped ledger continued")
    return after


def expect_error(fn):
    try: fn()
    except Exception as exc:
        demand(isinstance(exc,(ValueError,TypeError,ArithmeticError)) or type(exc).__name__=="LedgerError",
               "unexpected exception instead of validation error: "+type(exc).__name__)
        return
    raise CheckError("invalid scalar/record accepted")


@case("QR007-C01", "A01 A02 A03 A04 A05 A17 A22 A34", "exact arithmetic, units and scalar rejection")
def arithmetic(api):
    for args, expected in [((10,"0.001","49900","0.0005"),"-0.2495"),
                           ((10,"0.001","49900","-0.0001"),"0.0499"),
                           ((0,"0.001","49900","0.0005"),"0"),
                           ((100,"0.001","2","0.5"),"-0.1"),
                           ((25,"0.001","2","0.5"),"-0.025")]:
        demand(api.fee_cash(*args)==expected,"fee literal")
    for q, rate, expected in [(10,"0.0001","-0.05"),(-10,"0.0001","0.05"),(10,"-0.0001","0.05"),(-10,"-0.0001","-0.05"),(10,"0","0")]:
        demand(api.funding_cash(q,"0.001","50000",rate)==expected,"funding sign literal")
    demand(api.realized_pnl(1,"1","101","110")=="9","slippage charged twice")
    demand(api.realized_pnl(-1,"1","110","101")=="9","short price sign")
    demand(api.seconds_to_us(86400)==86400000000 and type(api.seconds_to_us(1)) is int,"time units")
    demand(api.seconds_to_us("1.000001")==1000001,"microsecond conversion")
    for value in (True,1.5,"0.0000001","NaN"):
        expect_error(lambda v=value:api.seconds_to_us(v))
    for q in (True,1.5): expect_error(lambda q=q:api.fee_cash(q,"0.001","49900","0.0005"))
    for p in ("NaN","-1","0","1e3","01",".1",10.0,True):
        expect_error(lambda p=p:api.fee_cash(0,"0.001",p,"0.0005"))
    expect_error(lambda:api.fee_cash(10,"0.001","49900","0.05%"))
    with localcontext() as ctx:
        ctx.prec=3
        demand(api.fee_cash(10,"0.001","49900","0.0005")=="-0.2495","ambient precision leaked")


@case("QR007-C02", "A10 A12 A17", "pro-rata residuals, signed/zero and coarse-quantum rejection")
def allocations(api):
    for total, expected in [("0.01",["0.0033","0.0033","0.0034"]),("-0.01",["-0.0033","-0.0033","-0.0034"]),("0",["0","0","0"])]:
        demand(api.allocate_pro_rata(total,[1,1,1],"0.0001")==expected,"allocation literal")
    demand(api.allocate_pro_rata("0",[],"0.01")==[],"zero empty")
    for args in [("0.02",[6,6,6,2],"0.01"),("-0.02",[6,6,6,2],"0.01"),("1",[],"0.01"),("0",[0,1],"0.01"),("0",[-1,1],"0.01"),("1",[True],"0.01")]:
        expect_error(lambda args=args:api.allocate_pro_rata(*args))


def a11_fixture(partial=False):
    f=Fixture(calendar=[(BTC,"s",20*U)]); r=f.unit("o",0,10)
    f.reserve(); f.mark("m10",10*U,"49900"); f.mark("m20",20*U,"50000")
    f.fill("o",10*U,10,"49900"); f.post("p-o","fee-o",10*U,"-0.2495",[(r,"-0.2495")])
    f.snapshot("s",20*U,[r]); f.revision("fund-s","s",20*U,20*U,"-0.05",[(r,"-0.05")])
    if partial:
        f.fill("c6",30*U,-6,"50100"); f.post("p-c6","fee-c6",30*U,"-0.1503",[(f.unit("o",0,6),"-0.1503")])
        f.fill("c4",35*U,-4,"50100"); f.post("p-c4","fee-c4",35*U,"-0.1002",[(f.unit("o",6,10),"-0.1002")])
    else:
        f.fill("c",30*U,-10,"50100"); f.post("p-c","fee-c",30*U,"-0.2505",[(r,"-0.2505")])
    f.post("p-f","fund-s",40*U,"-0.05",[(r,"-0.05")])
    return f


@case("QR007-C03", "A07 A11 A18 A19 A20", "A11 all four financial states and availability equality")
def a11_states(api):
    ledger,cfg,_,receipt=apply_fixture(api,a11_fixture())
    checkpoints=[(10,balance("9999.7505","0","0","0","9999.7505","9999.7505"),10),
                 (20,balance("9999.7505","0","0.05","1","10000.7005","9999.7005"),10),
                 (30,balance("10001.5","0","0.05","0","10001.45","10001.45"),0),
                 (40,balance("10001.45","0","0","0","10001.45","10001.45"),0)]
    for t, expected, q in checkpoints:
        check_snapshot(ledger.snapshot(t*U),cfg,expected,{"lot:o":q})
    demand(ledger.snapshot(10*U-1)["balances"]["cash_usdt"]=="10000","fee leaked before available")
    cash=sum((money(e["cash_delta_usdt"]) for e in receipt["entries"]),Fraction(0))
    demand(cash==Fraction("1.45"),"journal cash sum")
    final=ledger.snapshot(40*U)
    demand({o["obligation_id"] for o in final["obligations"]}=={"fee-o","fee-c","fund-s"},"extra/missing obligations")


@case("QR007-C04", "A12", "partial FIFO fees/funding and natural episode slice totals")
def partial_fifo(api):
    ledger,cfg,_,_=apply_fixture(api,a11_fixture(True))
    s=check_snapshot(ledger.snapshot(40*U),cfg,balance("10001.45","0","0","0","10001.45","10001.45"),{"lot:o":0})
    rows=sorted(s["closed_slices"],key=lambda v:v["unit_start"])
    demand(len(rows)==2,"partial slice count")
    expected=[(0,6,"1.2","-0.1497","-0.1503","-0.03","0.87"),(6,10,"0.8","-0.0998","-0.1002","-0.02","0.58")]
    for row,(lo,hi,pnl,entry,exit_fee,fund,net) in zip(rows,expected):
        demand((row["unit_start"],row["unit_end"],row["realized_price_pnl_usdt"],row["entry_fee_cash_usdt"],row["exit_fee_cash_usdt"],row["funding_cash_usdt"])==(lo,hi,pnl,entry,exit_fee,fund),"partial allocation literal")
        demand(sum(map(Fraction,[pnl,entry,exit_fee,fund]))==Fraction(net),"slice net oracle")


@case("QR007-C05", "A07 A10 A14", "reversal belongs to two episodes; old funding and fee refund stay old")
def reversal_late_fee(api):
    f=Fixture(calendar=[(BTC,"s",20*U)]); old=f.unit("o",0,10); new=f.unit("r",0,6)
    f.reserve(); f.mark("m",10*U,"50000");f.fill("o",10*U,10,"50000")
    f.post("p-o","fee-o",10*U,"-0.25",[(old,"-0.25")]);f.snapshot("s",20*U,[old])
    f.revision("fund-s","s",20*U,25*U,"-0.05",[(old,"-0.05")])
    f.fill("r",30*U,-16,"50000");f.post("p-r","fee-r",30*U,"-0.4",[(old,"-0.25"),(new,"-0.15")])
    f.post("p-f","fund-s",40*U,"-0.05",[(old,"-0.05")])
    f.revision("fee-o","o",10*U,50*U,"-0.2",[(old,"-0.2")],rev=2,kind="fee")
    f.post("refund","fee-o",60*U,"0.05",[(old,"0.05")],corrects="p-o")
    ledger,cfg,_,_=apply_fixture(api,f)
    for t,exp in [(40,balance("9999.3","0","0","0","9999.3","9999.3")),
                  (50,balance("9999.3","0.05","0","0","9999.35","9999.3")),
                  (60,balance("9999.35","0","0","0","9999.35","9999.35"))]:
        s=check_snapshot(ledger.snapshot(t*U),cfg,exp,{"lot:o":0,"lot:r":6})
        demand(len(s["closed_slices"])==1 and s["closed_slices"][0]["episode_id"]=="episode:o","reversal episode")
        row=s["closed_slices"][0]
        demand(row["exit_fee_cash_usdt"]=="-0.25" and row["funding_cash_usdt"]=="-0.05","reversal cash attribution")
        demand(row["entry_fee_cash_usdt"]==("-0.25" if t==40 else "-0.2"),"late fee attribution")


def flat_funding(total="-0.05", initial_available=4*U, initial_post=True):
    f=Fixture(cash="1000",fee="0",calendar=[(BTC,"s",2*U)]);r=f.unit("o",0,10)
    f.reserve();f.fill("o",U,10,"100");f.snapshot("s",2*U,[r]);f.fill("c",3*U,-10,"100")
    f.revision("fund-s","s",2*U,initial_available,total,[(r,total)] if total is not None else [])
    if initial_post:f.post("p1","fund-s",5*U,"-0.05",[(r,"-0.05")])
    return f,r


@case("QR007-C06", "A13 A14", "cumulative T versus independent partial bookings, sign reversal and refund")
def revisions_postings(api):
    f,r=flat_funding()
    for rev,t,total in [(2,10,"-0.1"),(3,11,"-0.08"),(4,15,"0.02")]:
        f.revision("fund-s","s",2*U,t*U,total,[(r,total)],rev=rev)
    f.post("p2","fund-s",12*U,"-0.02",[(r,"-0.02")]);f.post("p3","fund-s",13*U,"-0.01",[(r,"-0.01")])
    f.post("refund","fund-s",16*U,"0.1",[(r,"0.1")],corrects="p1")
    ledger,cfg,_,_=apply_fixture(api,f)
    for t,c,a,l,e in [(5,"999.95","0","0","999.95"),(10,"999.95","0","0.05","999.9"),
                       (11,"999.95","0","0.03","999.92"),(12,"999.93","0","0.01","999.92"),
                       (13,"999.92","0","0","999.92"),(15,"999.92","0.1","0","1000.02"),(16,"1000.02","0","0","1000.02")]:
        budget=finite_decimal(Fraction(c)-Fraction(l))
        check_snapshot(ledger.snapshot(t*U),cfg,balance(c,a,l,"0",e,budget),{"lot:o":0})


@case("QR007-C07", "A19 A29", "R06 known cash while total unknown; unknown-to-known and back")
def unknown_total(api):
    f,r=flat_funding(total=None,initial_post=False)
    f.post("partial","fund-s",10*U,"-0.02",[(r,"-0.02")])
    f.revision("fund-s","s",2*U,20*U,"-0.05",[(r,"-0.05")],rev=2)
    f.revision("fund-s","s",2*U,30*U,None,[],rev=3)
    ledger,cfg,_,receipt=apply_fixture(api,f)
    for t,exp in [(10,balance("999.98",None,None,"0",None)),(20,balance("999.98","0","0.03","0","999.95","999.95")),(30,balance("999.98",None,None,"0",None))]:
        s=check_snapshot(ledger.snapshot(t*U),cfg,exp,{"lot:o":0})
        obligation(s,"fund-s",B_usdt="-0.02")
    rows={e["source_key"]["record_id"]+":"+str(e["source_key"]["revision"]):e for e in receipt["entries"]}
    for key,reason in [("partial:1","UNKNOWN_OBLIGATION_TOTAL"),("fund-s:2","UNKNOWN_PRIOR_BALANCE"),("fund-s:3","UNKNOWN_CURRENT_BALANCE")]:
        e=rows[key]
        for field in ("pending_delta_usdt","receivable_delta_usdt","liability_delta_usdt"):
            demand(e[field] is None and e["null_reasons"][field]==reason,"R06 conditional delta")
    demand(rows["partial:1"]["cash_delta_usdt"]=="-0.02","unknown total lost known cash")


@case("QR007-C08", "A18 A19 A27", "R01 future-fact perturbation rehashes catalogue, leaves past causal hash")
def future_perturbation(api):
    f,r=flat_funding(initial_available=20*U,initial_post=False)
    other=copy.deepcopy(f)
    revision=next(v for v in other.records if v["record_type"]=="ObligationRevision")
    revision["cumulative_signed_total_usdt"]="-0.08";revision["allocations"][0]["signed_cash_usdt"]="-0.08"
    left,cfg1,_,_=apply_fixture(api,f);right,cfg2,_,_=apply_fixture(api,other)
    a=check_snapshot(left.snapshot(10*U),cfg1,balance("1000",None,None,"0",None),{"lot:o":0})
    b=check_snapshot(right.snapshot(10*U),cfg2,balance("1000",None,None,"0",None),{"lot:o":0})
    demand(a==b,"future fact altered earlier snapshot/hash")
    demand(left.audit()["config_sha256"]!=right.audit()["config_sha256"],"audit failed to bind future fact")
    demand(left.snapshot(20*U)["state_sha256"]!=right.snapshot(20*U)["state_sha256"],"available changed fact missing")


@case("QR007-C09", "A08 A09 A18", "R02 late origin guard independent of batch order/grouping")
def late_origin(api):
    for order in ("forward","reverse","alone","prefix"):
        f=Fixture(fee="0",calendar=[(BTC,"s",8*U)])
        if order=="prefix":
            f.snapshot("s",8*U,[]);f.fill("o",7*U,10,"100",available=9*U)
            rejected(api,f,"LATE_ORIGIN_UNSUPPORTED",prefix=(0,));continue
        f.fill("o",7*U,10,"100",available=9*U)
        if order!="alone":f.snapshot("s",8*U,[f.unit("o",0,10)])
        if order=="reverse":f.records.reverse()
        rejected(api,f,"LATE_ORIGIN_UNSUPPORTED")
    f=Fixture(fee="0",calendar=[(BTC,"s",8*U)]);f.fill("o",7*U,10,"100");f.snapshot("s",8*U,[f.unit("o",0,10)])
    ledger,cfg,_,_=apply_fixture(api,f)
    check_snapshot(ledger.snapshot(8*U),cfg,quantities={"lot:o":10})


@case("QR007-C10", "A15 A18 A30 A33", "R03 causal mark and delayed final rate, no time flooring")
def formula_clock(api):
    def make(future=False):
        f=Fixture(cash="1000",fee="0",calendar=[(BTC,"s",80*U)]);r=f.unit("o",0,10)
        f.reserve();f.fill("o",70*U,10,"50000");f.snapshot("s",80*U,[r]);f.mark("m",79*U,"50000")
        calc=dict(kind="funding_formula",signed_contracts=10,multiplier="0.001",mark_price="50000",final_rate="0.0001",
                  valuation_at_us=79*U,valuation_available_at_us=(90 if future else 79)*U,rate_available_at_us=95*U,
                  valuation_rule_id=f.rule("valuation"),multiplier_rule_id=f.rule("multiplier"))
        rev=f.revision("fund-s","s",80*U,100*U,"-0.05",[(r,"-0.05")],calculation=calc);rev["known_at_us"]=95*U
        return f
    rejected(api,make(True),"FUTURE_PROXY_MARK")
    ledger,cfg,_,_=apply_fixture(api,make())
    check_snapshot(ledger.snapshot(99*U),cfg,balance("1000",None,None,"0",None),{"lot:o":10})
    check_snapshot(ledger.snapshot(100*U),cfg,balance("1000","0","0.05","0","999.95","999.95"),{"lot:o":10})
    bad=make();snap=next(r for r in bad.records if r["record_type"]=="FundingSnapshot");snap["source_t_seconds"]=83
    rejected(api,bad)


@case("QR007-C11", "A21 A29", "R04 assertion admission, staleness, current heads and historical queries")
def readiness_heads(api):
    for authority in ("authority",None):
        f,r=flat_funding()
        f.assertion(10*U,[("fee-o",1),("fee-c",1),("fund-s",1)],["p1"],authority=authority)
        f.revision("fund-s","s",2*U,20*U,"-0.08",[(r,"-0.08")],rev=2)
        f.post("p2","fund-s",21*U,"-0.03",[(r,"-0.03")]);f.assertion(22*U,[("fee-o",1),("fee-c",1),("fund-s",2)],["p1","p2"],revision=2)
        ledger,cfg,records,_=apply_fixture(api,f)
        ordered=api.Ledger(copy.deepcopy(cfg))
        for at in sorted({v["available_at_us"] for v in records}):
            check_receipt(ordered.apply_batch([copy.deepcopy(v) for v in records if v["available_at_us"]==at]))
        for t,status,complete in [(10,"complete" if authority else "invalid",10*U if authority else None),
                                  (20,"immature" if authority else "invalid",None),(21,"immature" if authority else "invalid",None),(22,"complete",22*U)]:
            actual=ledger.readiness("episode:o",t*U);shape("Readiness",actual)
            demand(actual["status"]==status and actual["complete_at_us"]==complete and actual["natural_exit_at_us"]==3*U,"readiness oracle")
            demand(actual==ordered.readiness("episode:o",t*U),"grouping changed readiness")
        demand(ledger.audit()["integrity"]=="clean","legal supersession latched integrity")


@case("QR007-C12", "A17 A27", "R05 two-asset ownership and cross-instrument references")
def two_assets(api):
    f=Fixture(cash="1000",assets=(BTC,ETH),fee="0")
    for inst,name,q,p in [(BTC,"btc",2,"100"),(ETH,"eth",3,"200")]:
        f.reserve(inst);f.mark("mark-"+name,U,p,inst);f.fill(name,U,q,p,inst)
    ledger,cfg,_,_=apply_fixture(api,f)
    check_snapshot(ledger.snapshot(U),cfg,balance("1000","0","0","0","1000","1000"),{"lot:btc":2,"lot:eth":3})
    conflict=Fixture(assets=(BTC,ETH),fee="0");conflict.fill("same",U,2,"100",BTC);conflict.fill("same",U,3,"200",ETH)
    rejected(api,conflict,"ID_SCOPE_CONFLICT")
    cross=copy.deepcopy(f);cross.post("cross","fee-btc",2*U,"-1",[(cross.unit("btc",0,2),"-1")],ETH)
    rejected(api,cross)


@case("QR007-C13", "A13 A17", "idempotence, rehashed identity conflict and atomic bad nested batch")
def atomic_and_duplicate(api):
    f=a11_fixture();ledger,cfg,records,_=apply_fixture(api,f)
    before=ledger.audit();receipt=ledger.apply_batch(copy.deepcopy(records));check_receipt(receipt)
    demand(receipt["status"]=="duplicate" and receipt["entries"]==[],"duplicate transition")
    demand(ledger.audit()["committed_state"]==before["committed_state"],"duplicate changed economic state")
    f=Fixture(fee="0");f.fill("o",U,10,"100")
    bad=f.post("bad","fee-o",2*U,"-1",[(f.unit("o",0,10),"-1")]);bad["allocations"][0]["unit_end"]=0
    rejected(api,f)
    f=Fixture(fee="0");f.fill("o",U,10,"100");f.fill("o",U,10,"101")
    rejected(api,f,prefix=(0,))
    f,_=flat_funding();next(r for r in f.records if r["record_type"]=="Posting")["revision"]=2
    rejected(api,f,"UNSUPPORTED_POSTING_RESTATEMENT")


@case("QR007-C14", "A18 A27", "input immutability and deep copies for all inspection views")
def deep_copies(api):
    f=a11_fixture();ledger,cfg,records,receipt=apply_fixture(api,f)
    pristine=ledger.snapshot(40*U);audit=ledger.audit()
    changed=ledger.snapshot(40*U);changed["balances"]["cash_usdt"]="0";changed["lots"][0]["closed_slice_ids"].append("bad")
    altered=ledger.audit();altered["committed_state"]["records"].clear();receipt["entries"].clear()
    cfg["initial_cash_usdt"]="1";records[0]["record_id"]="mutated"
    demand(ledger.snapshot(40*U)==pristine and ledger.audit()==audit,"mutable output/input alias")
    _,records=f.seal();original=copy.deepcopy(records[0]);normalized=api.validate_record(records[0])
    shape("Record",normalized);normalized["source_refs"].clear()
    demand(records[0]==original,"validate_record mutated source")


@case("QR007-C15", "A06 A19 A29 A33", "missing snapshot, unresolved mapping and explicit empty calendar")
def missing_coverage(api):
    for mode in ("missing","mapping"):
        f=Fixture(cash="1000",fee="0",calendar=[(BTC,"s",2*U)]);f.reserve();f.fill("o",U,10,"100");f.fill("c",3*U,-10,"100")
        if mode=="mapping":
            r=f.snapshot("s",2*U,[f.unit("o",0,10)]);r["mapping_rule_id"]=None;r["null_reasons"]["mapping_rule_id"]="UNKNOWN_MAPPING"
        ledger,cfg,_,_=apply_fixture(api,f)
        snap=check_snapshot(ledger.snapshot(4*U),cfg,balance("1000",None,None,"0",None),{"lot:o":0})
        demand(snap["coverage_issues"]==[dict(instrument_id=BTC,event_id="s",reason_code="MISSING_EXPECTED_SNAPSHOT" if mode=="missing" else "UNRESOLVED_SNAPSHOT_MAPPING")],"coverage issue missing")
        ready=ledger.readiness("episode:o",4*U);shape("Readiness",ready);demand(ready["status"]=="immature","unknown coverage finalized")
    f=Fixture(cash="1000",fee="0");f.reserve();f.fill("o",U,10,"100");f.fill("c",3*U,-10,"100")
    ledger,cfg,_,_=apply_fixture(api,f)
    check_snapshot(ledger.snapshot(4*U),cfg,balance("1000","0","0","0","1000","1000"),{"lot:o":0})


@case("QR007-C16", "A20 A30", "C/A/L kept separate, no unrealized-gain spending; stale mark blocks")
def conservative_budget(api):
    f=Fixture(cash="1000",fee="0",multiplier="1",calendar=[(BTC,"a",10*U),(BTC,"l",20*U)]);r=f.unit("o",0,1)
    f.reserve(margin="100",fees="5");f.fill("o",U,1,"100")
    for name,t,total in [("a",10,"20"),("l",20,"-30")]:
        f.snapshot(name,t*U,[r]);f.revision("fund-"+name,name,t*U,t*U,total,[(r,total)])
    for t,p in [(30,"100"),(40,"150"),(50,"60")]:f.mark("m"+str(t),t*U,p)
    ledger,cfg,_,_=apply_fixture(api,f)
    for t,u,e,b in [(30,"0","990","865"),(40,"50","1040","865"),(50,"-40","950","825")]:
        check_snapshot(ledger.snapshot(t*U),cfg,balance("1000","20","30",u,e,b),{"lot:o":1})
    check_snapshot(ledger.snapshot(110*U),cfg,balance("1000","20","30","-40","950","825"))
    stale=check_snapshot(ledger.snapshot(110*U+1),cfg,balance("1000","20","30",None,None))
    demand(stale["balances"]["reductions_supported"] is True,"unknown mark erased exit support")


@case("QR007-C17", "A09", "snapshot-before-fills four boundary eligibility examples")
def tie_eligibility(api):
    for variant,expected in [("close_at",10),("open_at",0),("add_at",4),("reduce_at",6)]:
        f=Fixture(fee="0",calendar=[(BTC,"s",20*U)])
        if variant=="open_at":
            f.fill("o",20*U,10,"100");ranges=[]
        elif variant=="add_at":
            f.fill("o",10*U,4,"100");f.fill("add",20*U,6,"100");ranges=[f.unit("o",0,4)]
        else:
            f.fill("o",10*U,10,"100")
            if variant=="reduce_at":f.fill("pre",15*U,-4,"100")
            f.fill("at",20*U,-expected,"100");ranges=[f.unit("o",10-expected,10)]
        f.snapshot("s",20*U,ranges)
        ledger,cfg,_,_=apply_fixture(api,f);s=check_snapshot(ledger.snapshot(20*U),cfg)
        o=obligation(s,"fund-s",T_usdt=None if expected else "0")
        if expected:demand(o["latest_revision"] is None,"unknown funding genesis fabricated")


@case("QR007-C18", "A03 A08 A16 A17 A27 A31 A32", "strict canonical/input schema, source binding and unsupported modes")
def canonical_types(api):
    f=Fixture(fee="0");f.fill("o",U,10,"100");cfg,records=f.seal();r=records[0]
    demand(api.canonical_bytes(r)==canonical(r),"canonical bytes")
    demand(api.content_sha256(r)==independent_content(r),"content hash preimage")
    changed=copy.deepcopy(r);changed["created_at_us"]+=1;changed["source_refs"][0]["source_row"]+=1
    demand(api.content_sha256(changed)==api.content_sha256(r),"provenance affected content hash")
    changed=copy.deepcopy(r);changed["available_at_us"]+=1
    demand(api.content_sha256(changed)!=api.content_sha256(r),"availability omitted from identity")
    changed=copy.deepcopy(r);changed["fill_price"]="+100.000"
    normalized=api.validate_record(changed);shape("Record",normalized);demand(normalized["fill_price"]=="100","normalization")
    for field,value in [("signed_contracts",True),("signed_contracts",1.5),("fill_price","NaN"),("available_at_us",True),("unexpected",0),("namespace","qf006"),("schema_version",2)]:
        changed=copy.deepcopy(r);changed[field]=value;expect_error(lambda c=changed:api.validate_record(c))
    bad=copy.deepcopy(f);bad.records[0]["evidence_mode"]="HISTORICAL_EXACT";rejected(api,bad,"OUT_OF_SCOPE_MODE")
    bad=copy.deepcopy(f);bad.config["rules"][0]["available_at_us"]=U;bc,_=bad.seal();expect_error(lambda:api.Ledger(bc))
    bad=copy.deepcopy(f);bad.records[0]["signed_contracts"]=0;rejected(api,bad,"ZERO_FILL")
    bc,br=f.seal();br[0]["source_refs"][0]["manifest_sha256"]="0"*64
    invalid=api.Ledger(bc);expect_error(lambda:invalid.apply_batch(br))


@case("QR007-C19", "A18 A29", "restated late booking is audit-only; original as-known state preserved")
def restated_view(api):
    f,r=flat_funding(initial_post=False);f.post("p1","fund-s",5*U,"-0.05",[(r,"-0.05")],available=8*U)
    ledger,cfg,_,_=apply_fixture(api,f)
    before=check_snapshot(ledger.snapshot(6*U),cfg,balance("1000","0","0.05","0","999.95","999.95"),{"lot:o":0})
    restated=ledger.restated(6*U,8*U)
    check_snapshot(restated,cfg,balance("999.95","0","0","0","999.95"),{"lot:o":0})
    demand(restated["view"]=="restated" and restated["knowledge_cutoff_us"]==8*U,"restated clocks")
    demand(ledger.snapshot(6*U)==before,"restated rewrote causal history")


@case("QR007-C20", "A07 A09 A12", "units closed before snapshot receive no later funding")
def presnapshot_partial(api):
    f=Fixture(cash="1000",fee="0",calendar=[(BTC,"s",20*U)]);r=f.unit("o",4,10)
    f.reserve();f.fill("o",10*U,10,"100");f.fill("pre",15*U,-4,"100");f.snapshot("s",20*U,[r])
    f.revision("fund-s","s",20*U,25*U,"-0.03",[(r,"-0.03")]);f.fill("post",30*U,-6,"100")
    f.post("p","fund-s",40*U,"-0.03",[(r,"-0.03")])
    ledger,cfg,_,_=apply_fixture(api,f)
    s=check_snapshot(ledger.snapshot(40*U),cfg,balance("999.97","0","0","0","999.97","999.97"),{"lot:o":0})
    demand([(r["unit_start"],r["unit_end"],r["funding_cash_usdt"]) for r in sorted(s["closed_slices"],key=lambda v:v["unit_start"])]==[(0,4,"0"),(4,10,"-0.03")],"snapshot eligibility leaked to preclosed units")


@case("QR007-C21", "A12 A24", "FIFO across added lots, one economic episode; slices are not labels")
def added_lots(api):
    f=Fixture(cash="1000",fee="0",calendar=[(BTC,"s",20*U)]);r1=f.unit("o",0,6);r2=f.unit("add",0,4);r2["episode_id"]="episode:o"
    f.reserve();f.fill("o",10*U,6,"100");f.fill("add",12*U,4,"100");f.snapshot("s",20*U,[r1,r2])
    f.revision("fund-s","s",20*U,25*U,"-0.05",[(r1,"-0.03"),(r2,"-0.02")]);f.fill("c7",30*U,-7,"100");f.fill("c3",35*U,-3,"100")
    f.post("p","fund-s",40*U,"-0.05",[(r1,"-0.03"),(r2,"-0.02")])
    ledger,cfg,_,_=apply_fixture(api,f)
    s=check_snapshot(ledger.snapshot(40*U),cfg,balance("999.95","0","0","0","999.95","999.95"),{"lot:o":0,"lot:add":0})
    rows=sorted(s["closed_slices"],key=lambda v:(v["closed_at_us"],v["lot_id"],v["unit_start"]))
    wanted={ ("lot:o",0,6):"-0.03", ("lot:add",0,1):"-0.005", ("lot:add",1,4):"-0.015" }
    demand({(r["lot_id"],r["unit_start"],r["unit_end"]):r["funding_cash_usdt"] for r in rows}==wanted,"added-lot FIFO")
    demand(all(r["episode_id"]=="episode:o" for r in rows),"adds fabricated new episode")


DEFERRED = {
    "A03":"order cancellation/selection integration and no-fill target", "A06":"actual event-calendar completeness",
    "A08":"historical exact sequence evidence", "A15":"historical MARK coverage", "A16":"historical metadata effectiveness",
    "A21":"market label maturity/export", "A22":"fold/cross-asset purge beyond time arithmetic",
    "A23":"cross-fold full-state/censoring", "A24":"episode denominator and target export",
    "A25":"no-fill selection labels", "A26":"full-state policy counterfactual",
    "A27":"native adapter integration", "A28":"fit authorization and train-only preprocessing; no real fit negative test",
    "A29":"market label finality", "A30":"actual mark proxy coverage/calibration",
    "A31":"historical conversion implementation; current profile rejects exact mode",
    "A32":"historical rule publication evidence", "A33":"actual source-to-snapshot mapping",
    "A34":"execution price formation/full replay beyond given-fill PnL",
}


def criteria_map():
    return {f"QF006-A{i:02}":dict(
        cases=[cid for cid,criteria,_,_ in CASES if f"A{i:02}" in criteria],
        scope="synthetic stage-1 primitive only" if any(f"A{i:02}" in c for _,c,_,_ in CASES) else "deferred",
        remaining=DEFERRED.get(f"A{i:02}","implementation execution still required; no historical truth claim")) for i in range(1,35)}


def result_base():
    return dict(namespace="qr007.independent-ledger-validation",schema_version=1,
                profile=PROFILE,approved_schema_commit=SCHEMA_COMMIT,approved_schema_sha256=SCHEMA_SHA256,
                validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                criteria=criteria_map(),pending_contracts=list(PENDING_CONTRACTS),
                limitations=["Synthetic ledger only; no market/replay/label/training readiness.",
                             "No real model/scaler/calibrator fit is invoked as a negative test.",
                             "Python socket guard is not an OS sandbox for arbitrary code.",
                             "Market research is gated on reliable volume and a newly accepted precision/aggregation version; price-only was rejected."],
                market_requests=0,model_fits=0)


def prepared_report():
    result=result_base()
    result.update(status="PREPARED_NOT_EXECUTED",target=None,producer_executed=False,
                  cases=[dict(case_id=cid,criteria=list(criteria),purpose=purpose,status="NOT_EXECUTED") for cid,criteria,purpose,_ in CASES],
                  totals=dict(prepared=len(CASES),passed=0,failed=0,not_executed=len(CASES)))
    return result


@contextmanager
def offline():
    def forbidden(*args,**kwargs): raise CheckError("Network disabled during offline verification")
    original=(socket.create_connection,socket.socket.connect,socket.socket.connect_ex)
    socket.create_connection=socket.socket.connect=socket.socket.connect_ex=forbidden
    try:yield
    finally:socket.create_connection,socket.socket.connect,socket.socket.connect_ex=original


def regular_explicit_file(path,maximum):
    path=Path(path).absolute()
    demand(not any(p.is_symlink() for p in (path,*path.parents)),"symlink input forbidden")
    demand(path.is_file() and path.stat().st_size<=maximum,"explicit regular file missing/too large")
    return path,path.read_bytes()


def load_target(path,sha256,commit,schema_path):
    """Only an explicitly handed-off, committed byte identity can be executed."""
    demand(not PENDING_CONTRACTS,"contract amendment pending: cannot execute producer yet")
    demand(H_RE.fullmatch(sha256 or "") and re.fullmatch(r"[0-9a-f]{40}",commit or ""),"exact SHA256 and Git commit required")
    schema_path,schema=regular_explicit_file(schema_path,1024*1024)
    demand(hashlib.sha256(schema).hexdigest()==SCHEMA_SHA256,"schema differs from reviewed bytes")
    path,source=regular_explicit_file(path,2*1024*1024)
    demand(path.name=="event_ledger.py" and hashlib.sha256(source).hexdigest()==sha256,"target identity differs")
    root=Path(subprocess.check_output(["git","-C",str(path.parent),"rev-parse","--show-toplevel"],text=True).strip())
    relative=path.relative_to(root).as_posix()
    committed=subprocess.check_output(["git","-C",str(root),"show",commit+":"+relative])
    demand(committed==source,"working target is not exact handed-off commit")
    schema_relative=schema_path.relative_to(root).as_posix()
    demand(subprocess.check_output(["git","-C",str(root),"show",commit+":"+schema_relative])==schema,"target commit does not contain approved schema")
    tree=ast.parse(source,filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            names=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module or ""]
            demand(not isinstance(node,ast.ImportFrom) or node.level==0,"relative/application imports prohibited")
            for name in names:demand(name.split(".")[0] in sys.stdlib_module_names,"producer must use standard library only")
    name="_qr007_pinned_"+sha256[:16];module=types.ModuleType(name);module.__file__=str(path)
    previous=sys.modules.get(name);sys.modules[name]=module
    try:
        with offline():exec(compile(source,str(path),"exec"),module.__dict__)
    finally:
        if previous is None:sys.modules.pop(name,None)
        else:sys.modules[name]=previous
    required=("Ledger","LedgerError","validate_record","canonical_bytes","content_sha256","seconds_to_us",
              "fee_cash","funding_cash","realized_pnl","allocate_pro_rata")
    demand(all(callable(getattr(module,k,None)) for k in required),"public API missing")
    return module,dict(path=str(path),sha256=sha256,commit=commit,schema_sha256=SCHEMA_SHA256,profile=PROFILE)


def execute_cases(api,identity):
    demand(not PENDING_CONTRACTS,"contract amendment pending: prepared cases cannot execute yet")
    result=result_base();rows=[]
    with offline():
        for cid,criteria,purpose,fn in CASES:
            row=dict(case_id=cid,criteria=list(criteria),purpose=purpose)
            try:fn(api)
            except Exception as exc:
                row.update(status="FAIL",error_type=type(exc).__name__,detail=str(exc)[:1000])
            else:row["status"]="PASS"
            rows.append(row)
    passed=sum(r["status"]=="PASS" for r in rows)
    result.update(status="PASS_SYNTHETIC_ONLY" if passed==len(rows) else "FAIL_SYNTHETIC",
                  target=identity,producer_executed=True,cases=rows,
                  totals=dict(prepared=len(rows),passed=passed,failed=len(rows)-passed,not_executed=0))
    return result


def strict_json(body):
    def pairs(items):
        result=dict(items);demand(len(result)==len(items),"duplicate JSON key");return result
    def invalid(value):raise CheckError("nonfinite JSON constant: "+value)
    return json.loads(body,object_pairs_hook=pairs,parse_constant=invalid)


def inspect_snapshot_artifact(path,state):
    """Independently inspect explicit A11 output, including rehashed corruption.

    This checks one artifact, not a producer implementation or complete replay.
    """
    path,body=regular_explicit_file(path,4*1024*1024);value=strict_json(body)
    literals={"entry":(10,balance("9999.7505","0","0","0","9999.7505","9999.7505"),10),
              "funding":(20,balance("9999.7505","0","0.05","1","10000.7005","9999.7005"),10),
              "closed":(30,balance("10001.5","0","0.05","0","10001.45","10001.45"),0),
              "settled":(40,balance("10001.45","0","0","0","10001.45","10001.45"),0)}
    demand(state in literals,"explicit literal state required")
    t,expected,quantity=literals[state];cfg,records=a11_fixture().seal()
    check_snapshot(value,cfg,expected,{"lot:o":quantity},records=records)
    demand(value["as_of_us"]==value["knowledge_cutoff_us"]==t*U and value["view"]=="as_known","artifact cutoff")
    return dict(status="PASS_ONE_LITERAL_SNAPSHOT_ONLY",artifact_sha256=hashlib.sha256(body).hexdigest(),
                profile=PROFILE,schema_sha256=SCHEMA_SHA256,state=state,producer_executed=False,training_ready=False)


def write_result(path,result):
    """Explicit new path, bounded JSON; atomic publish without replacing a file."""
    path=Path(path).absolute()
    demand(not any(p.is_symlink() for p in (path,*path.parents)),"symlink output forbidden")
    demand(path.parent.is_dir() and not path.exists(),"output must be new with existing parent")
    body=(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
    demand(len(body)<=4*1024*1024,"result too large")
    temp=None
    try:
        with tempfile.NamedTemporaryFile(prefix=".qr007-",suffix=".tmp",dir=path.parent,delete=False) as stream:
            temp=Path(stream.name);stream.write(body);stream.flush();os.fsync(stream.fileno())
        os.link(temp,path)  # Atomic, fails if an existing destination wins the race.
    finally:
        if temp is not None:temp.unlink(missing_ok=True)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare",action="store_true")
    mode.add_argument("--target",type=Path)
    mode.add_argument("--snapshot",type=Path)
    parser.add_argument("--target-sha256");parser.add_argument("--target-commit")
    parser.add_argument("--schema",type=Path);parser.add_argument("--literal-state",choices=("entry","funding","closed","settled"))
    parser.add_argument("--output",type=Path)
    args=parser.parse_args(argv)
    if args.prepare:
        demand(not any((args.target_sha256,args.target_commit,args.schema,args.literal_state)),"prepare must not name target execution arguments")
        result=prepared_report()
    elif args.snapshot:
        demand(not any((args.target_sha256,args.target_commit,args.schema)),"snapshot inspection does not execute or attest a target")
        result=inspect_snapshot_artifact(args.snapshot,args.literal_state)
    else:
        demand(args.schema and args.target_sha256 and args.target_commit,"execution requires schema/path/commit/SHA256")
        api,identity=load_target(args.target,args.target_sha256,args.target_commit,args.schema)
        result=execute_cases(api,identity)
    if args.output:write_result(args.output,result)
    print(json.dumps(result,sort_keys=True,allow_nan=False))
    return 1 if result["status"].startswith("FAIL") else 0


if __name__=="__main__":
    raise SystemExit(main())

"""In-memory qd007-synthetic-r3 ledger (reviewed r2 + B1). No I/O, market, application or model imports.

The immutable journal is reprojected for each information cutoff. Fractions keep
cash exact; only declared attribution quantum rounds. Not a market replay engine.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import re

NS = "qd007.synthetic-ledger"
PROFILE = "qd007-synthetic-r3"
INSTRUMENTS = ("gate:usdt:BTC_USDT", "gate:usdt:ETH_USDT")
LIMIT = 2**63 - 1
COMMON = "namespace schema_version record_type record_id revision instrument_id trajectory_id scenario_id evidence_mode created_at_us available_at_us source_time_precision source_refs null_reasons".split()
FIELDS = {
    "Fill": "order_id decision_id decision_at_us filled_at_us sequence signed_contracts fill_price multiplier multiplier_rule_id fee_fraction fee_rule_id liquidity_role role_basis fee_currency fee_obligation_id",
    "FundingSnapshot": "nominal_settlement_at_us snapshot_at_us snapshot_sequence source_t_seconds source_record_at_us mapping_rule_id obligation_id eligible_ranges",
    "ObligationRevision": "obligation_kind origin_id supersedes_revision authority_id rule_id economic_at_us known_at_us cumulative_signed_total_usdt allocations calculation",
    "Posting": "obligation_id signed_amount_usdt booking_at_us booking_known_at_us booking_basis booking_rule_id corrects_posting_id allocations",
    "CompletenessAssertion": "supersedes_revision authority_id finality_rule_id scope obligation_revision_refs posting_refs asserted_at_us known_at_us",
    "Valuation": "valuation_at_us known_at_us price_kind mark_price valuation_rule_id multiplier_rule_id",
    "Reserves": "effective_at_us expires_at_us known_at_us reserved_margin_usdt reserved_fees_usdt excludes_counted_losses_liabilities_and_posted_fees",
}


class LedgerError(ValueError):
    def __init__(self, code, json_pointer="/", **details):
        super().__init__(code + " at " + json_pointer)
        self.code, self.json_pointer = code, json_pointer
        self.receipt = dict(code=code, json_pointer=json_pointer,
            recoverable_identity=None, input_sha256=None, incumbent_sha256=None,
            committed_sha256="0" * 64, disposition="reject",
            null_reasons=dict(recoverable_identity="UNKNOWN_INPUT_IDENTITY",
                input_sha256="NONCANONICAL_INPUT", incumbent_sha256="NO_INCUMBENT"))
        self.receipt.update(details)


def _require(ok, code="SCHEMA_VIOLATION", path="/"):
    if not ok:
        raise LedgerError(code, path)


def _shape(x, fields, path="/"):
    _require(type(x) is dict and set(x) == set(fields.split() if isinstance(fields, str) else fields), path=path)


def _int(x, low=0, high=LIMIT):
    _require(type(x) is int and low <= x <= high, "INTEGER_CONTRACT_VIOLATION")
    return x


def _id(x):
    _require(type(x) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", x), "INVALID_ID")
    return x


def _hash(x):
    _require(type(x) is str and re.fullmatch(r"[0-9a-f]{64}", x), "INVALID_HASH")
    return x


def _number(x, minimum=None, positive=False):
    _require(type(x) is str and re.fullmatch(r"[+-]?(0|[1-9][0-9]*)(\.[0-9]+)?", x), "INVALID_DECIMAL")
    _require(sum(c.isdigit() for c in x) <= 128 and (len(x.split(".")[1]) if "." in x else 0) <= 64, "DECIMAL_BOUNDS")
    n = Fraction(x)
    _require((minimum is None or n >= minimum) and (not positive or n > 0), "DECIMAL_DOMAIN")
    return n


def _fmt(n):
    n = Fraction(n)
    if not n:
        return "0"
    d, a, b = n.denominator, 0, 0
    while d % 2 == 0:
        d //= 2; a += 1
    while d % 5 == 0:
        d //= 5; b += 1
    _require(d == 1, "NONTERMINATING_AMOUNT")
    scale = max(a, b)
    integer = abs(n.numerator) * 2**(scale-a) * 5**(scale-b)
    digits = str(integer).rjust(scale+1, "0")
    value = digits if not scale else (digits[:-scale] + "." + digits[-scale:]).rstrip("0").rstrip(".")
    return ("-" if n < 0 else "") + value


def _json(x):
    if x is None or type(x) in (str, bool, int):
        return
    if type(x) is list:
        for v in x: _json(v)
    elif type(x) is dict:
        for k, v in x.items():
            _require(type(k) is str, "JSON_KEY_TYPE"); _json(v)
    else:
        raise LedgerError("NONCANONICAL_INPUT")


def _bytes(x):
    _json(x)
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def _digest(x):
    return hashlib.sha256(_bytes(x)).hexdigest()


def _set(values):
    _require(type(values) is list)
    result = sorted(values, key=_bytes)
    _require(len({_bytes(v) for v in result}) == len(result), "DUPLICATE_SET_MEMBER")
    return result


def canonical_bytes(value):
    if type(value) is dict and value.get("namespace") == NS and "record_type" in value:
        value = validate_record(value)
    elif type(value) is dict and value.get("namespace") == NS and "source_manifest" in value:
        value = Ledger._config_check(value)
    return _bytes(value)


def content_sha256(record):
    r = validate_record(record)
    return _digest({k: v for k, v in r.items() if k not in ("created_at_us", "source_refs")})


def seconds_to_us(value):
    n = Fraction(_int(value)) if type(value) is int else _number(value, 0)
    result = n * 1000000
    _require(result.denominator == 1, "FRACTIONAL_MICROSECOND")
    return _int(result.numerator)


def fee_cash(quantity, multiplier, fill_price, fee_fraction):
    q = _int(quantity, -LIMIT)
    return _fmt(-abs(q) * _number(multiplier, positive=True) * _number(fill_price, positive=True) * _number(fee_fraction))


def funding_cash(signed_contracts, multiplier, mark_price, final_rate):
    q = _int(signed_contracts, -LIMIT)
    return _fmt(-q * _number(multiplier, positive=True) * _number(mark_price, positive=True) * _number(final_rate))


def realized_pnl(signed_closed_contracts, multiplier, entry_price, exit_price):
    q = _int(signed_closed_contracts, -LIMIT)
    m = _number(multiplier, positive=True)
    return _fmt(q * m * (_number(exit_price, positive=True) - _number(entry_price, positive=True)))


def _quantum(value):
    q = _number(value, positive=True)
    s = _fmt(q)
    _require(s.replace(".", "").strip("0") == "1", "INVALID_QUANTUM")
    return q


def _allocate(total, weights, quantum):
    _require(type(weights) is list)
    for w in weights: _int(w, 1)
    if not weights:
        _require(total == 0, "EMPTY_ALLOCATION"); return []
    result = []
    for w in weights[:-1]:
        share = total * w / sum(weights) / quantum
        integer, rem = divmod(abs(share.numerator), share.denominator)
        if rem * 2 > share.denominator or rem * 2 == share.denominator and integer % 2:
            integer += 1
        result.append(integer * quantum * (-1 if share < 0 else 1))
    result.append(total - sum(result))
    _require(all(abs(v) <= abs(total) and (not v or v * total >= 0) for v in result), "ALLOCATION_QUANTUM_TOO_COARSE")
    return result


def allocate_pro_rata(total, weights, quantum):
    return [_fmt(v) for v in _allocate(_number(total), weights, _quantum(quantum))]


def _nulls(r, allowed):
    _require(type(r["null_reasons"]) is dict, "NULL_REASON_CONTRACT")
    expected = {k for k in allowed if r[k] is None}
    _require(set(r["null_reasons"]) == expected, "NULL_REASON_CONTRACT")
    for k in expected:
        _require(r["null_reasons"][k] in allowed[k], "NULL_REASON_CONTRACT", "/"+k)


def _range(r, allocation=False):
    fields = "lot_id episode_id unit_start unit_end" + (" allocation_id signed_cash_usdt" if allocation else "")
    _shape(r, fields)
    for f in ("lot_id", "episode_id"): _id(r[f])
    _int(r["unit_start"]); _int(r["unit_end"], 1)
    _require(r["unit_start"] < r["unit_end"], "INVALID_UNIT_RANGE")
    if allocation:
        _hash(r["allocation_id"])
        r["signed_cash_usdt"] = _fmt(_number(r["signed_cash_usdt"]))


def validate_record(record):
    try:
        return _validate_record(record)
    except LedgerError:
        raise
    except (TypeError, KeyError, ValueError, IndexError) as exc:
        raise LedgerError("SCHEMA_VIOLATION") from exc


def _validate_record(record):
    _json(record)
    _require(type(record) is dict)
    typ = record.get("record_type")
    _require(typ in FIELDS, "UNSUPPORTED_RECORD_TYPE")
    _shape(record, COMMON + FIELDS[typ].split())
    r = deepcopy(record)
    _require(r["namespace"] == NS, "UNSUPPORTED_NAMESPACE")
    _require(type(r["schema_version"]) is int and r["schema_version"] == 1, "UNSUPPORTED_VERSION")
    _require(r["evidence_mode"] == "SCENARIO", "OUT_OF_SCOPE_MODE")
    _require(r["instrument_id"] in INSTRUMENTS, "OUT_OF_SCOPE_INSTRUMENT")
    for f in ("record_id", "trajectory_id", "scenario_id"): _id(r[f])
    _int(r["revision"], 1)
    _require(r["source_time_precision"] in ("seconds", "milliseconds", "microseconds"), "INVALID_PRECISION")
    _require(type(r["source_refs"]) is list and r["source_refs"], "MISSING_PROVENANCE")
    for ref in r["source_refs"]:
        _shape(ref, "manifest_sha256 source_id source_row")
        _hash(ref["manifest_sha256"]); _id(ref["source_id"]); _int(ref["source_row"], 1)
    r["source_refs"] = _set(r["source_refs"])
    allowed = {}
    null = lambda field, reason: allowed.update({field: (reason,)})
    if typ == "Fill": null("sequence", "UNKNOWN_SEQUENCE")
    if typ == "FundingSnapshot":
        for f in ("nominal_settlement_at_us", "mapping_rule_id"): null(f, "UNKNOWN_MAPPING")
        null("snapshot_sequence", "UNKNOWN_SEQUENCE")
        for f in ("source_t_seconds", "source_record_at_us"): null(f, "UNKNOWN_SOURCE_TIME")
    if typ in ("ObligationRevision", "CompletenessAssertion"): null("supersedes_revision", "NOT_APPLICABLE")
    if typ == "ObligationRevision":
        for f in ("cumulative_signed_total_usdt", "calculation"): null(f, "UNKNOWN_AMOUNT")
    if typ == "Posting": null("corrects_posting_id", "NOT_APPLICABLE")
    if typ == "CompletenessAssertion": null("authority_id", "UNKNOWN_FINALITY")
    if typ == "Valuation": null("mark_price", "UNKNOWN_MARK")
    if typ == "Reserves":
        for f in ("reserved_margin_usdt", "reserved_fees_usdt"): null(f, "UNKNOWN_AMOUNT")
    if typ == "Posting" and (r["booking_at_us"] is None or r["booking_known_at_us"] is None):
        raise LedgerError("UNRESOLVED_POSTING_NOT_APPLIED")
    _nulls(r, allowed)
    _require(all(v is not None or field in allowed for field,v in r.items()),"NULL_REASON_CONTRACT")
    for f, v in r.items():
        if v is None: continue
        if f.endswith("_at_us") or f in ("expires_at_us",): _int(v)
        elif f.endswith("_id") and f not in ("instrument_id",): _id(v)
    if typ not in ("ObligationRevision", "CompletenessAssertion"):
        _require(r["revision"] == 1, "UNSUPPORTED_POSTING_RESTATEMENT" if typ == "Posting" else "UNSUPPORTED_REVISION")
    if typ == "Fill":
        _require(len(r["record_id"]) <= 96, "OVERLONG_ORIGIN_ID")
        _int(r["signed_contracts"], -LIMIT); _require(r["signed_contracts"] != 0, "ZERO_FILL")
        if r["sequence"] is not None: _int(r["sequence"], 1)
        for f in ("fill_price", "multiplier"): r[f] = _fmt(_number(r[f], positive=True))
        r["fee_fraction"] = _fmt(_number(r["fee_fraction"]))
        _require(r["liquidity_role"] in ("maker", "taker"), "UNKNOWN_LIQUIDITY_ROLE")
        _require(r["role_basis"] == "scenario" and r["fee_currency"] == "USDT", "UNIT_OR_ROLE_VIOLATION")
        _require(r["decision_at_us"] <= r["filled_at_us"] <= r["available_at_us"], "CLOCK_CONTRADICTION")
    elif typ == "FundingSnapshot":
        if r["snapshot_sequence"] is not None: _int(r["snapshot_sequence"], 1)
        _require((r["source_t_seconds"] is None) == (r["source_record_at_us"] is None), "CLOCK_CONTRADICTION")
        if r["source_t_seconds"] is not None:
            _int(r["source_t_seconds"])
            _require(r["source_t_seconds"]*1000000 == r["source_record_at_us"] <= r["available_at_us"], "CLOCK_CONTRADICTION")
        _require(r["snapshot_at_us"] <= r["available_at_us"], "CLOCK_CONTRADICTION")
        _require(type(r["eligible_ranges"]) is list)
        for v in r["eligible_ranges"]: _range(v)
    elif typ == "ObligationRevision":
        _require(r["obligation_kind"] in ("fee", "funding"))
        if r["supersedes_revision"] is not None: _int(r["supersedes_revision"], 1)
        v = r["cumulative_signed_total_usdt"]
        if v is not None: r["cumulative_signed_total_usdt"] = _fmt(_number(v))
        _require(type(r["allocations"]) is list)
        for v in r["allocations"]: _range(v, True)
        c = r["calculation"]
        _require((c is None) == (r["cumulative_signed_total_usdt"] is None), "CALCULATION_CONTRACT")
        if c is None: _require(not r["allocations"], "ALLOCATION_MISMATCH")
        else:
            _require(type(c) is dict and c.get("kind") in ("authoritative_total", "funding_formula"), "CALCULATION_CONTRACT")
            if c["kind"] == "authoritative_total": _shape(c, "kind")
            else:
                _shape(c, "kind signed_contracts multiplier mark_price final_rate valuation_at_us valuation_available_at_us rate_available_at_us valuation_rule_id multiplier_rule_id")
                _int(c["signed_contracts"], -LIMIT); _require(c["signed_contracts"] != 0)
                for f in ("multiplier", "mark_price"): c[f] = _fmt(_number(c[f], positive=True))
                c["final_rate"] = _fmt(_number(c["final_rate"]))
                for f in ("valuation_at_us", "valuation_available_at_us", "rate_available_at_us"): _int(c[f])
                _id(c["valuation_rule_id"]); _id(c["multiplier_rule_id"])
        _require(r["economic_at_us"] <= r["known_at_us"] <= r["available_at_us"], "CLOCK_CONTRADICTION")
    elif typ == "Posting":
        _require(r["booking_at_us"] is not None and r["booking_known_at_us"] is not None, "UNRESOLVED_POSTING_NOT_APPLIED")
        r["signed_amount_usdt"] = _fmt(_number(r["signed_amount_usdt"]))
        _require(r["signed_amount_usdt"] != "0", "ZERO_POSTING")
        _require(r["booking_basis"] == "scenario")
        _require(r["booking_at_us"] <= r["booking_known_at_us"] <= r["available_at_us"], "CLOCK_CONTRADICTION")
        _require(type(r["allocations"]) is list)
        for v in r["allocations"]: _range(v, True)
    elif typ == "CompletenessAssertion":
        if r["supersedes_revision"] is not None: _int(r["supersedes_revision"], 1)
        sc = r["scope"]
        _shape(sc, "instrument_id trajectory_id episode_id event_kinds economic_from_us economic_to_exclusive_us")
        _require(sc["instrument_id"] in INSTRUMENTS)
        for f in ("trajectory_id", "episode_id"): _id(sc[f])
        _int(sc["economic_from_us"]); _int(sc["economic_to_exclusive_us"])
        _require(sc["economic_from_us"] < sc["economic_to_exclusive_us"], "INVALID_SCOPE")
        sc["event_kinds"] = _set(sc["event_kinds"])
        _require(set(sc["event_kinds"]) <= {"fill", "fee", "funding", "posting"})
        for field, idfield in (("obligation_revision_refs", "obligation_id"), ("posting_refs", "posting_id")):
            r[field] = _set(r[field])
            for ref in r[field]:
                _shape(ref, [idfield, "revision"]); _id(ref[idfield]); _int(ref["revision"], 1)
                if idfield == "posting_id": _require(ref["revision"] == 1, "UNSUPPORTED_POSTING_RESTATEMENT")
        _require(r["asserted_at_us"] <= r["known_at_us"] <= r["available_at_us"], "CLOCK_CONTRADICTION")
    elif typ == "Valuation":
        _require(r["price_kind"] == "MARK", "WRONG_PRICE_KIND")
        if r["mark_price"] is not None: r["mark_price"] = _fmt(_number(r["mark_price"], positive=True))
        _require(r["valuation_at_us"] <= r["known_at_us"] <= r["available_at_us"], "CLOCK_CONTRADICTION")
    else:
        for f in ("reserved_margin_usdt", "reserved_fees_usdt"):
            if r[f] is not None: r[f] = _fmt(_number(r[f], 0))
        _require(type(r["excludes_counted_losses_liabilities_and_posted_fees"]) is bool and r["excludes_counted_losses_liabilities_and_posted_fees"], "DOUBLE_COUNTED_RESERVES")
        _require(r["effective_at_us"] <= r["known_at_us"] <= r["available_at_us"] < r["expires_at_us"], "CLOCK_CONTRADICTION")
    return r


def _key(r):
    return {f: r[f] for f in ("instrument_id", "record_type", "record_id", "revision")}


def _identity(r):
    return (r["instrument_id"], r["record_type"], r["record_id"], r["revision"])


def _econ(r):
    return r[{"Fill":"filled_at_us", "FundingSnapshot":"snapshot_at_us", "ObligationRevision":"economic_at_us", "Posting":"booking_at_us", "Valuation":"valuation_at_us", "Reserves":"effective_at_us", "CompletenessAssertion":"asserted_at_us"}[r["record_type"]]]


def _unit(lot, start, end):
    return dict(lot_id=lot["lot_id"], episode_id=lot["episode_id"], unit_start=start, unit_end=end)


class Ledger:
    def __init__(self, config):
        try:
            self._config = self._config_check(config)
        except LedgerError:
            raise
        except (TypeError, KeyError, ValueError, IndexError) as exc:
            raise LedgerError("SCHEMA_VIOLATION") from exc
        self._rules = {r["rule_id"]: r for r in self._config["rules"]}
        self._records, self._corroborating, self._failures = {}, [], []
        self._entries = []
        self._policy_hash = _digest({k:v for k,v in self._config.items() if k != "source_manifest"})
        self._manifest_hash = _digest(self._config["source_manifest"])
        self._sources = {(r["source_id"],r["source_row"]):r["payload_sha256"] for r in self._config["source_manifest"]["rows"]}

    @staticmethod
    def _config_check(config):
        _json(config)
        _shape(config, "namespace schema_version ledger_id trajectory_id scenario_id instruments initial_at_us end_exclusive_us initial_cash_usdt allocation_quantum_usdt rules expected_funding_snapshots source_manifest")
        c = deepcopy(config)
        _require(c["namespace"] == NS, "UNSUPPORTED_NAMESPACE")
        _require(type(c["schema_version"]) is int and c["schema_version"] == 1, "UNSUPPORTED_VERSION")
        for f in ("ledger_id","trajectory_id","scenario_id"): _id(c[f])
        c["instruments"] = _set(c["instruments"])
        _require(c["instruments"] and set(c["instruments"]) <= set(INSTRUMENTS), "OUT_OF_SCOPE_INSTRUMENT")
        _int(c["initial_at_us"]); _int(c["end_exclusive_us"])
        _require(c["initial_at_us"] < c["end_exclusive_us"])
        c["initial_cash_usdt"] = _fmt(_number(c["initial_cash_usdt"],0))
        c["allocation_quantum_usdt"] = _fmt(_quantum(c["allocation_quantum_usdt"]))
        _require(type(c["rules"]) is list)
        ids = set()
        for r in c["rules"]:
            _shape(r,"rule_id kind instrument_id valid_from_us valid_to_exclusive_us available_at_us authority_id parameters null_reasons")
            _id(r["rule_id"]); _id(r["authority_id"])
            _require(r["rule_id"] not in ids, "DUPLICATE_RULE"); ids.add(r["rule_id"])
            _require(r["instrument_id"] in c["instruments"])
            for f in ("valid_from_us","available_at_us"): _int(r[f])
            _nulls(r,{"valid_to_exclusive_us":("OPEN_ENDED_SCENARIO",)})
            if r["valid_to_exclusive_us"] is not None:
                _int(r["valid_to_exclusive_us"]); _require(r["valid_to_exclusive_us"] > r["valid_from_us"])
            _require(r["available_at_us"] <= c["initial_at_us"], "FUTURE_RULE")
            p,kind=r["parameters"],r["kind"]
            if kind=="fee":
                _shape(p,"role signed_fraction fee_currency"); _require(p["role"] in ("maker","taker") and p["fee_currency"]=="USDT")
                p["signed_fraction"]=_fmt(_number(p["signed_fraction"]))
            elif kind=="multiplier":
                _shape(p,"base_per_contract quantity_unit");p["base_per_contract"]=_fmt(_number(p["base_per_contract"],positive=True));_require(p["quantity_unit"]=="contracts")
            elif kind=="valuation":
                _shape(p,"price_kind max_age_us");_require(p["price_kind"]=="MARK");_int(p["max_age_us"],1)
            elif kind=="sequence":
                _shape(p,"same_time_order");_require(p["same_time_order"] in ("snapshot_before_fills","fills_before_snapshot"))
            elif kind in ("funding","booking","finality"):
                field="calendar" if kind=="funding" else "policy"
                _shape(p,[field]+(["authority_id"] if kind=="finality" else []))
                _require(p[field]==dict(funding="explicit_snapshot_list",booking="explicit_posting_records",finality="explicit_scoped_assertions")[kind])
                if kind=="finality":_id(p["authority_id"])
            else:raise LedgerError("UNSUPPORTED_RULE_KIND")
        for i,a in enumerate(c["rules"]):
            for b in c["rules"][i+1:]:
                if (a["kind"],a["instrument_id"],a["parameters"].get("role")) == (b["kind"],b["instrument_id"],b["parameters"].get("role")):
                    _require(max(a["valid_from_us"],b["valid_from_us"]) >= min(a["valid_to_exclusive_us"] or LIMIT,b["valid_to_exclusive_us"] or LIMIT),"OVERLAPPING_RULES")
        for inst in c["instruments"]:
            _require(len({r["parameters"]["base_per_contract"] for r in c["rules"] if r["instrument_id"]==inst and r["kind"]=="multiplier"})<=1,"MISSING_CONTRACT_CONVERSION")
        _require(type(c["expected_funding_snapshots"]) is list)
        seen=set()
        for x in c["expected_funding_snapshots"]:
            _shape(x,"instrument_id event_id snapshot_at_us mapping_rule_id")
            _require(x["instrument_id"] in c["instruments"]);_id(x["event_id"]);_id(x["mapping_rule_id"]);_int(x["snapshot_at_us"])
            _require(c["initial_at_us"]<=x["snapshot_at_us"]<c["end_exclusive_us"])
            _require(x["event_id"] not in seen,"ID_SCOPE_CONFLICT");seen.add(x["event_id"])
            candidates=[r for r in c["rules"] if r["rule_id"]==x["mapping_rule_id"] and r["kind"]=="funding" and r["instrument_id"]==x["instrument_id"] and r["valid_from_us"]<=x["snapshot_at_us"] and (r["valid_to_exclusive_us"] is None or x["snapshot_at_us"]<r["valid_to_exclusive_us"])]
            _require(candidates,"RULE_MISMATCH")
        c["expected_funding_snapshots"].sort(key=lambda x:(x["instrument_id"],x["snapshot_at_us"],x["event_id"]))
        m=c["source_manifest"]
        _shape(m,"namespace schema_version fixture_id rows");_require(m["namespace"]=="qd007.synthetic-sources" and type(m["schema_version"]) is int and m["schema_version"]==1)
        _id(m["fixture_id"]);_require(type(m["rows"]) is list)
        seen=set()
        for row in m["rows"]:
            _shape(row,"source_id source_row payload_sha256");_id(row["source_id"]);_int(row["source_row"],1);_hash(row["payload_sha256"])
            key=(row["source_id"],row["source_row"]);_require(key not in seen,"DUPLICATE_SOURCE");seen.add(key)
        m["rows"].sort(key=lambda x:(x["source_id"],x["source_row"]))
        return c

    def _rule(self, rule_id, kind, inst, at):
        r=self._rules.get(rule_id)
        _require(r is not None and r["kind"]==kind and r["instrument_id"]==inst and r["valid_from_us"]<=at and (r["valid_to_exclusive_us"] is None or at<r["valid_to_exclusive_us"]),"RULE_MISMATCH")
        return r["parameters"]

    def _one_rule(self, kind, inst, at):
        candidates=[r for r in self._rules.values() if r["kind"]==kind and r["instrument_id"]==inst and r["valid_from_us"]<=at and (r["valid_to_exclusive_us"] is None or at<r["valid_to_exclusive_us"])]
        _require(len(candidates)==1,"RULE_MISMATCH")
        return candidates[0]["parameters"]

    def _allocation_id(self, oid, unit, inst):
        c=self._config
        return _digest([c["ledger_id"],c["trajectory_id"],c["scenario_id"],inst,oid,unit["lot_id"],unit["unit_start"],unit["unit_end"]])

    def _allocations(self, oid, inst, ranges, total):
        amounts=_allocate(total,[u["unit_end"]-u["unit_start"] for u in ranges],Fraction(self._config["allocation_quantum_usdt"]))
        return [dict(u,allocation_id=self._allocation_id(oid,u,inst),signed_cash_usdt=_fmt(v)) for u,v in zip(ranges,amounts)]

    def _check_allocations(self, allocs, oid, origin, total):
        ranges=origin["ranges"];inst=origin["instrument"]
        # Allocation partitions may refine origin ranges, but cannot overlap/gap,
        # change FIFO order, or transfer ownership to another lot/episode.
        expected=[]
        remaining=list(allocs)
        for u in ranges:
            cursor=u["unit_start"]
            while remaining and remaining[0]["lot_id"]==u["lot_id"] and remaining[0]["unit_start"]<u["unit_end"]:
                a=remaining.pop(0)
                _require(a["episode_id"]==u["episode_id"] and a["unit_start"]==cursor and a["unit_end"]<=u["unit_end"],"ALLOCATION_MISMATCH")
                _require(a["allocation_id"]==self._allocation_id(oid,a,inst),"ALLOCATION_ID_MISMATCH")
                cursor=a["unit_end"];expected.append({k:a[k] for k in ("lot_id","episode_id","unit_start","unit_end")})
            _require(cursor==u["unit_end"],"ALLOCATION_MISMATCH")
        _require(not remaining,"ALLOCATION_MISMATCH")
        _require(allocs==self._allocations(oid,inst,expected,total),"ALLOCATION_MISMATCH")

    def _guard(self, records, old):
        owners={}
        def own(kind, ident, r):
            owner=(r["instrument_id"],r["trajectory_id"],r["scenario_id"])
            key=(kind,ident);_require(key not in owners or owners[key]==owner,"ID_SCOPE_CONFLICT");owners[key]=owner
        fills=[];vals={};reserves={}
        for r in records:
            inst=r["instrument_id"];typ=r["record_type"]
            _require(inst in self._config["instruments"] and all(r[k]==self._config[k] for k in ("trajectory_id","scenario_id")),"REFERENCE_SCOPE_MISMATCH")
            kind={"Fill":"fill","FundingSnapshot":"funding event","ObligationRevision":"obligation","Posting":"posting","CompletenessAssertion":"assertion","Valuation":"valuation","Reserves":"reserves"}[typ]
            own(kind,r["record_id"],r)
            if typ in ("Fill","FundingSnapshot","ObligationRevision","Valuation","Reserves"):
                _require(self._config["initial_at_us"]<=_econ(r)<self._config["end_exclusive_us"],"ORIGIN_OUT_OF_RANGE")
            if typ=="Fill":
                own("obligation",r["fee_obligation_id"],r)
                own("episode","episode:"+r["record_id"],r);own("lot","lot:"+r["record_id"],r)
                for action in ("open","close"):own("leg","leg:"+r["record_id"]+":"+action,r)
                fills.append(r)
                _require(r["multiplier"]==self._rule(r["multiplier_rule_id"],"multiplier",inst,r["filled_at_us"])["base_per_contract"],"MULTIPLIER_MISMATCH")
                fee=self._rule(r["fee_rule_id"],"fee",inst,r["filled_at_us"])
                _require(fee["role"]==r["liquidity_role"] and fee["signed_fraction"]==r["fee_fraction"],"FEE_RULE_MISMATCH")
                for s in self._config["expected_funding_snapshots"]:
                    if s["instrument_id"]!=inst:continue
                    before=self._one_rule("sequence",inst,s["snapshot_at_us"])["same_time_order"]=="fills_before_snapshot"
                    precedes=r["filled_at_us"]<s["snapshot_at_us"] or before and r["filled_at_us"]==s["snapshot_at_us"]
                    _require(not(precedes and r["available_at_us"]>s["snapshot_at_us"]),"LATE_ORIGIN_UNSUPPORTED")
            if typ=="FundingSnapshot":own("obligation",r["obligation_id"],r)
            if typ=="Valuation":
                self._rule(r["valuation_rule_id"],"valuation",inst,r["valuation_at_us"])
                self._rule(r["multiplier_rule_id"],"multiplier",inst,r["valuation_at_us"])
                key=(inst,r["valuation_at_us"])
                _require(key not in vals or vals[key]==r["mark_price"],"AMBIGUOUS_VALUATION");vals[key]=r["mark_price"]
            if typ=="Reserves":
                key=(inst,r["effective_at_us"],r["available_at_us"])
                content=tuple(r[f] for f in ("expires_at_us","reserved_margin_usdt","reserved_fees_usdt"))
                _require(key not in reserves or reserves[key]==content,"AMBIGUOUS_RESERVES");reserves[key]=content
        for inst in self._config["instruments"]:
            fs=sorted([f for f in fills if f["instrument_id"]==inst],key=lambda r:(r["available_at_us"],r["filled_at_us"],r["sequence"] or 0))
            for a,b in zip(fs,fs[1:]):
                if a["filled_at_us"]==b["filled_at_us"]:
                    _require(a["sequence"] is not None and b["sequence"] is not None and a["sequence"]!=b["sequence"],"AMBIGUOUS_FILL_SEQUENCE")
                _require((a["filled_at_us"],a["sequence"] or 0)<=(b["filled_at_us"],b["sequence"] or 0),"LATE_ORIGIN_UNSUPPORTED")
            prior=[r for r in old if r["record_type"]=="Fill" and r["instrument_id"]==inst]
            new=[r for r in fs if _identity(r) not in {_identity(o) for o in prior}]
            if prior and new:
                _require(min((r["filled_at_us"],r["sequence"] or 0) for r in new)>=max((r["filled_at_us"],r["sequence"] or 0) for r in prior),"LATE_ORIGIN_UNSUPPORTED")

    def _inventory(self, records):
        lots=[];slices=[];origins={};snapshots={};episodes={};fill_map={}
        def order(r):
            typ=r["record_type"];at=_econ(r)
            fill_first=self._one_rule("sequence",r["instrument_id"],at)["same_time_order"]=="fills_before_snapshot"
            phase=(0 if fill_first else 1) if typ=="Fill" else (1 if fill_first else 0)
            return (at,phase,r.get("sequence") or 0,r["record_id"])
        for r in sorted([r for r in records if r["record_type"] in ("Fill","FundingSnapshot")],key=order):
            inst=r["instrument_id"];at=_econ(r)
            if r["record_type"]=="FundingSnapshot":
                expected=next((x for x in self._config["expected_funding_snapshots"] if x["event_id"]==r["record_id"] and x["instrument_id"]==inst),None)
                _require(expected is not None and expected["snapshot_at_us"]==at,"UNDECLARED_SNAPSHOT")
                if r["mapping_rule_id"] is not None:
                    _require(r["mapping_rule_id"]==expected["mapping_rule_id"],"SNAPSHOT_MAPPING_MISMATCH")
                    self._rule(r["mapping_rule_id"],"funding",inst,at)
                live=[_unit(l,l["initial_contracts"]-l["remaining_contracts"],l["initial_contracts"]) for l in lots if l["instrument_id"]==inst and l["remaining_contracts"]]
                _require(r["eligible_ranges"]==live,"ELIGIBILITY_MISMATCH")
                oid=r["obligation_id"];_require(oid not in origins,"OBLIGATION_ORIGIN_CONFLICT")
                origins[oid]=dict(kind="funding",ranges=live,instrument=inst,origin=r,at=at,fee=None)
                snapshots[r["record_id"]]=r
                continue
            q=r["signed_contracts"];direction=1 if q>0 else -1;remain=abs(q);ranges=[];closing=[]
            active=[l for l in lots if l["instrument_id"]==inst and l["remaining_contracts"]]
            for l in active:
                _require(l["multiplier"]==r["multiplier"],"MISSING_CONTRACT_CONVERSION")
            if active and active[0]["direction"]!=("long" if direction>0 else "short"):
                for l in active:
                    take=min(remain,l["remaining_contracts"])
                    if not take:break
                    start=l["initial_contracts"]-l["remaining_contracts"];end=start+take
                    u=_unit(l,start,end);ranges.append(u)
                    sid=_digest([r["record_id"],l["lot_id"],start,end])
                    pnl=Fraction(realized_pnl(take*(1 if l["direction"]=="long" else -1),l["multiplier"],l["entry_price"],r["fill_price"]))
                    sl=dict(slice_id=sid,lot_id=l["lot_id"],episode_id=l["episode_id"],closing_fill_id=r["record_id"],closed_at_us=at,unit_start=start,unit_end=end,realized_price_pnl_usdt=_fmt(pnl),entry_fee_cash_usdt="0",exit_fee_cash_usdt="0",funding_cash_usdt="0",attribution_revision=1,null_reasons={})
                    slices.append(sl);closing.append(sl);l["closed_slice_ids"].append(sid)
                    l["remaining_contracts"]-=take;remain-=take
                    ep=episodes[l["episode_id"]]
                    if not any(x["remaining_contracts"] and x["episode_id"]==l["episode_id"] for x in lots):ep["exit"]=at
            if remain:
                active=[l for l in lots if l["instrument_id"]==inst and l["remaining_contracts"]]
                eid=active[0]["episode_id"] if active else "episode:"+r["record_id"]
                if eid not in episodes:episodes[eid]=dict(instrument=inst,entry=at,exit=None)
                l=dict(lot_id="lot:"+r["record_id"],episode_id=eid,instrument_id=inst,opening_fill_id=r["record_id"],opened_at_us=at,direction="long" if direction>0 else "short",initial_contracts=remain,remaining_contracts=remain,entry_price=r["fill_price"],multiplier=r["multiplier"],live_ranges=[],closed_slice_ids=[])
                lots.append(l);ranges.append(_unit(l,0,remain))
            oid=r["fee_obligation_id"];_require(oid not in origins,"OBLIGATION_ORIGIN_CONFLICT")
            origins[oid]=dict(kind="fee",ranges=ranges,instrument=inst,origin=r,at=at,fee=Fraction(fee_cash(q,r["multiplier"],r["fill_price"],r["fee_fraction"])))
            fill_map[r["record_id"]]=dict(record=r,closing=closing)
        for l in lots:
            l["live_ranges"]=[_unit(l,l["initial_contracts"]-l["remaining_contracts"],l["initial_contracts"])] if l["remaining_contracts"] else []
        return dict(lots=lots,slices=slices,origins=origins,snapshots=snapshots,episodes=episodes,fills=fill_map)

    def _finance(self, records, inventory, economic_cutoff, restated=False):
        origins=inventory["origins"];obs={};entries=[];cash=Fraction(self._config["initial_cash_usdt"])
        def levels(o):
            if o["T"] is None:return (None,None,None)
            p=o["T"]-o["B"]
            return p,max(p,Fraction(0)),max(-p,Fraction(0))
        def entry(source, transition, oid, before, after, dc=Fraction(0), sl=None):
            nonlocal cash
            cash+=dc
            nr={};o=obs.get(oid)
            eidset={a["episode_id"] for a in o["ranges"]} if o else {sl["episode_id"]}
            eid=next(iter(eidset)) if len(eidset)==1 else None
            aid=_digest([sl["slice_id"],"realized"]) if sl else None
            if aid is None:nr["allocation_id"]="AGGREGATE_OBLIGATION"
            if oid is None:nr["obligation_id"]="NOT_APPLICABLE"
            if eid is None:nr["episode_id"]="AGGREGATE_OBLIGATION"
            ds=[]
            for field,a,b in zip(("pending_delta_usdt","receivable_delta_usdt","liability_delta_usdt"),before,after):
                if a is None or b is None:
                    ds.append(None);nr[field]="UNKNOWN_OBLIGATION_TOTAL" if a is None and b is None else "UNKNOWN_PRIOR_BALANCE" if a is None else "UNKNOWN_CURRENT_BALANCE"
                else:ds.append(_fmt(b-a))
            key=_key(source)
            e=dict(entry_id=_digest([key,transition,oid if oid is not None else aid]),source_key=key,transition=transition,
                obligation_id=oid,allocation_id=aid,episode_id=eid,economic_at_us=o["at"] if o else source["filled_at_us"],available_at_us=source["available_at_us"],
                cash_delta_usdt=_fmt(dc),pending_delta_usdt=ds[0],receivable_delta_usdt=ds[1],liability_delta_usdt=ds[2],realized_pnl_usdt=_fmt(dc if sl else 0),null_reasons=nr)
            entries.append(e)
        def owner(r, o):
            _require(r["instrument_id"]==o["instrument"],"REFERENCE_SCOPE_MISMATCH")
            _require(r["available_at_us"]>=o["origin"]["available_at_us"],"CLOCK_CONTRADICTION")
        # Origin first at equal consumer time; revision ordering before posting is
        # deterministic. Finite source dependencies below are checked explicitly.
        priority={"Fill":0,"FundingSnapshot":0,"ObligationRevision":1,"Posting":2}
        events=sorted([r for r in records if r["record_type"] in priority],key=lambda r:(r["available_at_us"],priority[r["record_type"]],r["revision"],_identity(r)))
        # Forward corrects links are permitted only within a genuinely earlier/equal
        # available source, never guessed from current position or a later record.
        posting_by_id={r["record_id"]:r for r in records if r["record_type"]=="Posting"}
        for ident in posting_by_id:
            seen=set();cursor=ident
            while cursor in posting_by_id:
                _require(cursor not in seen,"DEPENDENCY_CYCLE");seen.add(cursor)
                cursor=posting_by_id[cursor]["corrects_posting_id"]
        for r in events:
            typ=r["record_type"]
            if typ in ("Fill","FundingSnapshot"):
                oid=r["fee_obligation_id"] if typ=="Fill" else r["obligation_id"]
                origin=origins[oid]
                total=origin["fee"] if typ=="Fill" else Fraction(0) if not origin["ranges"] and r["mapping_rule_id"] is not None else None
                revision=1 if total is not None else None
                allocs=self._allocations(oid,origin["instrument"],origin["ranges"],total) if total is not None else []
                o=dict(origin,T=total,B=Fraction(0),revision=revision,allocations=allocs,versions={},postings=[],available=r["available_at_us"],known=r["available_at_us"])
                obs[oid]=o
                if revision:o["versions"][1]=r
                if typ=="Fill":
                    for sl in inventory["fills"][r["record_id"]]["closing"]:
                        entry(r,"realized_pnl",None,(Fraction(0),)*3,(Fraction(0),)*3,Fraction(sl["realized_price_pnl_usdt"]),sl)
                    entry(r,"fee_claim",oid,(Fraction(0),)*3,levels(o))
            elif typ=="ObligationRevision":
                oid=r["record_id"];_require(oid in obs,"DANGLING_ORIGIN")
                o=obs[oid];owner(r,o)
                _require(r["origin_id"]==o["origin"]["record_id"] and r["obligation_kind"]==o["kind"] and r["economic_at_us"]==o["at"],"REFERENCE_SCOPE_MISMATCH")
                _require(r["revision"]==(o["revision"] or 0)+1 and r["supersedes_revision"]==o["revision"],"REVISION_GAP")
                _require(r["known_at_us"]>=o["known"] and r["available_at_us"]>=o["available"],"CLOCK_CONTRADICTION")
                self._rule(r["rule_id"],"fee" if o["kind"]=="fee" else "funding",r["instrument_id"],o["at"])
                _require(r["authority_id"]==self._rules[r["rule_id"]]["authority_id"],"UNPROVEN_AUTHORITY")
                total=None if r["cumulative_signed_total_usdt"] is None else Fraction(r["cumulative_signed_total_usdt"])
                if total is not None:self._check_allocations(r["allocations"],oid,o,total)
                c=r["calculation"]
                if c and c["kind"]=="funding_formula":
                    _require(o["kind"]=="funding","CALCULATION_CONTRACT")
                    at=o["at"];vr=self._rule(c["valuation_rule_id"],"valuation",o["instrument"],at)
                    mr=self._rule(c["multiplier_rule_id"],"multiplier",o["instrument"],at)
                    _require(c["valuation_at_us"]<=c["valuation_available_at_us"]<=at,"FUTURE_PROXY_MARK")
                    _require(at-c["valuation_at_us"]<=vr["max_age_us"],"STALE_VALUATION")
                    _require(max(at,c["valuation_available_at_us"],c["rate_available_at_us"])<=r["known_at_us"],"FUTURE_CALCULATION_INPUT")
                    quantity=sum((u["unit_end"]-u["unit_start"])*(1 if next(l for l in inventory["lots"] if l["lot_id"]==u["lot_id"])["direction"]=="long" else -1) for u in o["ranges"])
                    _require(quantity==c["signed_contracts"] and mr["base_per_contract"]==c["multiplier"],"MULTIPLIER_OR_QUANTITY_MISMATCH")
                    _require(total==Fraction(funding_cash(quantity,c["multiplier"],c["mark_price"],c["final_rate"])),"FORMULA_MISMATCH")
                before=levels(o)
                o.update(T=total,revision=r["revision"],allocations=r["allocations"],available=r["available_at_us"],known=r["known_at_us"])
                o["versions"][r["revision"]]=r
                after=levels(o)
                if before[0] is not None or after[0] is not None:entry(r,"fee_claim" if o["kind"]=="fee" else "funding_claim",oid,before,after)
            else:
                oid=r["obligation_id"];_require(oid in obs,"DANGLING_ORIGIN")
                o=obs[oid];owner(r,o)
                self._rule(r["booking_rule_id"],"booking",r["instrument_id"],o["at"])
                target=r["corrects_posting_id"]
                if target is not None:
                    p=posting_by_id.get(target)
                    _require(p is not None and p["obligation_id"]==oid and p["instrument_id"]==r["instrument_id"],"REFERENCE_SCOPE_MISMATCH")
                    _require(p["available_at_us"]<=r["available_at_us"] and target!=r["record_id"],"DEPENDENCY_CYCLE")
                amount=Fraction(r["signed_amount_usdt"]);self._check_allocations(r["allocations"],oid,o,amount)
                # In restated projections a later booking is outside economic e;
                # it is retained in journal but cannot move retrospective cash.
                if restated and r["booking_at_us"]>economic_cutoff:continue
                before=levels(o);o["B"]+=amount;o["postings"].append(r)
                entry(r,"cash_posting",oid,before,levels(o),amount)
        return obs,cash,entries

    def _assertion_check(self, records, inventory, obs):
        groups={}
        for r in records:
            if r["record_type"]!="CompletenessAssertion":continue
            groups.setdefault(r["record_id"],[]).append(r)
            sc=r["scope"];ep=inventory["episodes"].get(sc["episode_id"])
            _require(ep is not None,"UNKNOWN_EPISODE")
            _require(sc["instrument_id"]==ep["instrument"]==r["instrument_id"] and sc["trajectory_id"]==r["trajectory_id"],"REFERENCE_SCOPE_MISMATCH")
            p=self._rule(r["finality_rule_id"],"finality",r["instrument_id"],sc["economic_from_us"])
            if r["authority_id"] is not None:_require(r["authority_id"]==p["authority_id"],"UNPROVEN_FINALITY_AUTHORITY")
            for ref in r["obligation_revision_refs"]:
                o=obs.get(ref["obligation_id"])
                _require(o is not None and ref["revision"] in o["versions"],"DANGLING_REFERENCE")
                _require(o["instrument"]==r["instrument_id"] and any(u["episode_id"]==sc["episode_id"] for u in o["ranges"]),"REFERENCE_SCOPE_MISMATCH")
            for ref in r["posting_refs"]:
                matches=[p for o in obs.values() for p in o["postings"] if p["record_id"]==ref["posting_id"]]
                _require(matches and matches[0]["instrument_id"]==r["instrument_id"],"REFERENCE_SCOPE_MISMATCH")
                _require(any(u["episode_id"]==sc["episode_id"] for u in matches[0]["allocations"]),"REFERENCE_SCOPE_MISMATCH")
        for group in groups.values():
            prev=None
            for r in sorted(group,key=lambda r:r["revision"]):
                _require(r["revision"]==(prev["revision"]+1 if prev else 1) and r["supersedes_revision"]==(prev["revision"] if prev else None),"REVISION_GAP")
                if prev:_require(r["known_at_us"]>=prev["known_at_us"] and r["available_at_us"]>=prev["available_at_us"],"CLOCK_CONTRADICTION")
                prev=r

    def _coverage(self, records, cutoff):
        snaps={r["record_id"]:r for r in records if r["record_type"]=="FundingSnapshot"}
        return [dict(instrument_id=x["instrument_id"],event_id=x["event_id"],reason_code="MISSING_EXPECTED_SNAPSHOT" if x["event_id"] not in snaps else "UNRESOLVED_SNAPSHOT_MAPPING")
                for x in self._config["expected_funding_snapshots"] if x["snapshot_at_us"]<=cutoff and (x["event_id"] not in snaps or snaps[x["event_id"]]["mapping_rule_id"] is None)]

    def _attribution(self, inv, obs, coverage):
        slices=inv["slices"];quantum=Fraction(self._config["allocation_quantum_usdt"])
        amounts={s["slice_id"]:dict(entry=Fraction(0),exit=Fraction(0),funding=Fraction(0)) for s in slices}
        contributions={s["slice_id"]:{} for s in slices}
        for oid,o in obs.items():
            for base in o["ranges"]:
                touched=[s for s in slices if s["lot_id"]==base["lot_id"] and max(s["unit_start"],base["unit_start"])<min(s["unit_end"],base["unit_end"])]
                for s in touched:
                    contributions[s["slice_id"]][oid]=o["revision"] or 0
                    if o["T"] is None:
                        kind="funding" if o["kind"]=="funding" else "exit" if s["closing_fill_id"]==o["origin"]["record_id"] else "entry"
                        amounts[s["slice_id"]][kind]=None
            for a in o["allocations"]:
                touched=[s for s in slices if s["lot_id"]==a["lot_id"] and max(s["unit_start"],a["unit_start"])<min(s["unit_end"],a["unit_end"])]
                remaining=Fraction(a["signed_cash_usdt"]);units=a["unit_end"]-a["unit_start"]
                for s in touched:
                    take=min(s["unit_end"],a["unit_end"])-max(s["unit_start"],a["unit_start"])
                    share=remaining if take==units else _allocate(remaining,[take,units-take],quantum)[0]
                    remaining-=share;units-=take
                    kind="funding" if o["kind"]=="funding" else "exit" if s["closing_fill_id"]==o["origin"]["record_id"] else "entry"
                    if amounts[s["slice_id"]][kind] is not None:amounts[s["slice_id"]][kind]+=share
        bad_inst={x["instrument_id"] for x in coverage}
        lot_map={l["lot_id"]:l for l in inv["lots"]}
        for s in slices:
            s["attribution_revision"]=1+sum(contributions[s["slice_id"]].values())
            nr={}
            for kind,field in (("entry","entry_fee_cash_usdt"),("exit","exit_fee_cash_usdt"),("funding","funding_cash_usdt")):
                n=amounts[s["slice_id"]][kind]
                reason="UNKNOWN_OBLIGATION_TOTAL"
                if kind=="funding" and lot_map[s["lot_id"]]["instrument_id"] in bad_inst:n=None;reason="UNRESOLVED_SNAPSHOT_COVERAGE"
                s[field]=None if n is None else _fmt(n)
                if n is None:nr[field]=reason
            s["null_reasons"]=nr

    def _project(self, economic, knowledge, restated=False, records=None):
        all_records=list(self._records.values()) if records is None else records
        visible=[r for r in all_records if r["available_at_us"]<=knowledge and (_econ(r)<=economic or r["record_type"]=="CompletenessAssertion")]
        inv=self._inventory(visible)
        obs,cash,entries=self._finance(visible,inv,economic,restated)
        coverage=self._coverage(visible,economic)
        self._attribution(inv,obs,coverage)
        U=Fraction(0);ureason=None;vrefs=[];mreserve=Fraction(0);freserve=Fraction(0);reserve_reason=None;rrefs=[]
        for inst in self._config["instruments"]:
            held=[l for l in inv["lots"] if l["instrument_id"]==inst and l["remaining_contracts"]]
            if held:
                marks=[r for r in visible if r["record_type"]=="Valuation" and r["instrument_id"]==inst]
                mark=max(marks,key=lambda r:(r["valuation_at_us"],r["available_at_us"],r["record_id"])) if marks else None
                if mark is None or mark["mark_price"] is None:ureason="UNKNOWN_MARK"
                else:
                    vr=self._rule(mark["valuation_rule_id"],"valuation",inst,mark["valuation_at_us"])
                    if economic-mark["valuation_at_us"]>vr["max_age_us"]:ureason="STALE_VALUATION"
                    else:
                        vrefs.append(mark["record_id"])
                        multiplier=self._rule(mark["multiplier_rule_id"],"multiplier",inst,mark["valuation_at_us"])["base_per_contract"]
                        for lot in held:
                            _require(lot["multiplier"]==multiplier,"MISSING_CONTRACT_CONVERSION")
                            U+=Fraction(realized_pnl(lot["remaining_contracts"]*(1 if lot["direction"]=="long" else -1),multiplier,lot["entry_price"],mark["mark_price"]))
            reserves=[r for r in visible if r["record_type"]=="Reserves" and r["instrument_id"]==inst]
            reserve=max(reserves,key=lambda r:(r["available_at_us"],r["effective_at_us"],r["record_id"])) if reserves else None
            if reserve is None or reserve["expires_at_us"]<=economic or reserve["reserved_margin_usdt"] is None or reserve["reserved_fees_usdt"] is None:reserve_reason="UNKNOWN_RESERVES"
            else:
                rrefs.append(reserve["record_id"]);mreserve+=Fraction(reserve["reserved_margin_usdt"]);freserve+=Fraction(reserve["reserved_fees_usdt"])
        unknown="UNRESOLVED_SNAPSHOT_COVERAGE" if coverage else "UNKNOWN_OBLIGATION_TOTAL" if any(o["T"] is None for o in obs.values()) else None
        A=None if unknown else sum((max(o["T"]-o["B"],Fraction(0)) for o in obs.values()),Fraction(0))
        L=None if unknown else sum((max(o["B"]-o["T"],Fraction(0)) for o in obs.values()),Fraction(0))
        E=None if unknown or ureason else cash+A-L+U
        breason="RESTATED_VIEW" if restated else unknown or ureason or reserve_reason
        budget=None if breason else cash-L+min(U,Fraction(0))-mreserve-freserve
        nr={"actual_available_margin_usdt":"NOT_MODELED"}
        def val(field,n,reason):
            if reason:nr[field]=reason;return None
            return _fmt(n)
        balance=dict(as_of_us=economic,view="restated" if restated else "as_known",knowledge_cutoff_us=knowledge,cash_usdt=_fmt(cash),
            receivables_usdt=val("receivables_usdt",A,unknown),liabilities_usdt=val("liabilities_usdt",L,unknown),
            unrealized_usdt=val("unrealized_usdt",U,ureason),economic_equity_usdt=val("economic_equity_usdt",E,unknown or ureason),
            reserved_margin_usdt=val("reserved_margin_usdt",mreserve,reserve_reason),reserved_fees_usdt=val("reserved_fees_usdt",freserve,reserve_reason),
            simulated_budget_usdt=val("simulated_budget_usdt",budget,breason),actual_available_margin_usdt=None,
            new_risk_supported=budget is not None and budget>0,reductions_supported=True,valuation_refs=sorted(vrefs),reserve_refs=sorted(rrefs),null_reasons=nr)
        states=[]
        for oid,o in sorted(obs.items(),key=lambda item:(item[1]["instrument"],item[0])):
            unk=o["T"] is None;p=None if unk else o["T"]-o["B"]
            nr={k:"UNKNOWN_OBLIGATION_TOTAL" for k in ("T_usdt","P_usdt","A_usdt","L_usdt")} if unk else {}
            if o["revision"] is None:nr["latest_revision"]="UNKNOWN_AMOUNT"
            refs={a["allocation_id"] for a in o["allocations"]}|{a["allocation_id"] for posting in o["postings"] for a in posting["allocations"]}
            states.append(dict(instrument_id=o["instrument"],obligation_id=oid,kind=o["kind"],origin_id=o["origin"]["record_id"],latest_revision=o["revision"],
                T_usdt=None if unk else _fmt(o["T"]),B_usdt=_fmt(o["B"]),P_usdt=None if unk else _fmt(p),A_usdt=None if unk else _fmt(max(p,0)),L_usdt=None if unk else _fmt(max(-p,0)),
                allocation_refs=sorted(refs),posting_refs=sorted([_key(p) for p in o["postings"]],key=_bytes),null_reasons=nr))
        result=dict(namespace=NS,schema_version=1,profile=PROFILE,ledger_id=self._config["ledger_id"],trajectory_id=self._config["trajectory_id"],scenario_id=self._config["scenario_id"],view=balance["view"],as_of_us=economic,knowledge_cutoff_us=knowledge,
            causal_policy_sha256=self._policy_hash,balances=balance,lots=inv["lots"],closed_slices=inv["slices"],obligations=states,coverage_issues=coverage,null_reasons={})
        result["state_sha256"]=_digest(result)
        return result,entries,inv,obs,visible

    def _active(self):
        _require(not self._failures,"INTEGRITY_STOPPED")

    def apply_batch(self, records):
        self._active();before=self.audit()["committed_sha256"];current_record=None;incumbent=None
        try:
            _require(type(records) is list)
            candidate=deepcopy(self._records);corroborating=deepcopy(self._corroborating)
            applied=[];duplicates=[];corroborated=[]
            for raw in records:
                current_record=raw;incumbent=None;r=validate_record(raw);current_record=r;key=_identity(r)
                if key in candidate:
                    incumbent=candidate[key]
                    code={"ObligationRevision":"CONFLICTING_OBLIGATION_REVISION","Posting":"CONFLICTING_POSTING_REVISION"}.get(r["record_type"],"CONFLICTING_EVENT_REVISION")
                    _require(content_sha256(incumbent)==content_sha256(r),code)
                for ref in r["source_refs"]:
                    _require(ref["manifest_sha256"]==self._manifest_hash and self._sources.get((ref["source_id"],ref["source_row"]))==content_sha256(r),"SOURCE_HASH_MISMATCH")
                if key in candidate:
                    duplicates.append(_key(r))
                    extras=[ref for ref in r["source_refs"] if ref not in incumbent["source_refs"]]
                    for ref in extras:
                        item=dict(key=_key(r),source_ref=ref)
                        if item not in corroborating:corroborating.append(item)
                    if extras:corroborated.append(_key(r))
                else:candidate[key]=r;applied.append(_key(r))
            _require(len(candidate)<=4096,"FIXTURE_CAPACITY_EXCEEDED")
            all_records=list(candidate.values())
            # Cross-record admission failures concern the complete candidate;
            # never falsely attribute them to the last normalized input record.
            current_record=all_records;incumbent=None
            self._guard(all_records,list(self._records.values()))
            cutoff=max([self._config["initial_at_us"]]+[max(_econ(r),r["available_at_us"]) for r in all_records])
            _,entries,inv,obs,_=self._project(cutoff,cutoff,records=all_records)
            self._assertion_check(all_records,inv,obs)
            prior_ids={e["entry_id"] for e in self._entries}
            corroborating=sorted(corroborating,key=_bytes)
            after=_digest(dict(config=self._config,records=sorted(candidate.values(),key=_identity),derived_entries=entries,corroborating_source_refs=corroborating))
            receipt=deepcopy(dict(status="applied" if applied else "duplicate",applied_keys=sorted(applied,key=_bytes),duplicate_keys=sorted(duplicates,key=_bytes),corroborated_keys=sorted(corroborated,key=_bytes),
                entries=[e for e in entries if e["entry_id"] not in prior_ids],committed_before_sha256=before,committed_after_sha256=after))
            self._records=candidate;self._entries=entries;self._corroborating=corroborating
            return receipt
        except (LedgerError, TypeError, KeyError, ValueError, IndexError, StopIteration) as error:
            exc=error if isinstance(error,LedgerError) else LedgerError("SCHEMA_VIOLATION")
            receipt=deepcopy(exc.receipt);receipt["committed_sha256"]=before
            try:
                receipt["input_sha256"]=_digest(current_record);receipt["null_reasons"].pop("input_sha256",None)
            except (LedgerError,TypeError,ValueError):pass
            try:
                key=_key(current_record)
                _require(key["instrument_id"] in INSTRUMENTS and key["record_type"] in FIELDS)
                _id(key["record_id"]);_int(key["revision"],1)
                receipt["recoverable_identity"]=key;receipt["null_reasons"].pop("recoverable_identity",None)
            except (LedgerError,TypeError,ValueError):pass
            if incumbent is not None:receipt["incumbent_sha256"]=_digest(incumbent);receipt["null_reasons"].pop("incumbent_sha256",None)
            if "CONFLICT" in exc.code or exc.code=="UNSUPPORTED_POSTING_RESTATEMENT":receipt["disposition"]="quarantine"
            self._failures.append(receipt);exc.receipt=deepcopy(receipt)
            raise exc

    def snapshot(self, as_of_us):
        self._active();_int(as_of_us)
        return deepcopy(self._project(as_of_us,as_of_us)[0])

    def restated(self, economic_at_us, knowledge_cutoff_us):
        self._active();_int(economic_at_us);_int(knowledge_cutoff_us)
        _require(knowledge_cutoff_us>=economic_at_us,"CLOCK_CONTRADICTION")
        return deepcopy(self._project(economic_at_us,knowledge_cutoff_us,True)[0])

    def readiness(self, episode_id, as_of_us):
        self._active();_id(episode_id);_int(as_of_us)
        _,_,inv,obs,visible=self._project(as_of_us,as_of_us)
        ep=inv["episodes"].get(episode_id);_require(ep is not None,"UNKNOWN_EPISODE")
        heads={}
        for r in visible:
            if r["record_type"]=="CompletenessAssertion":
                if r["record_id"] not in heads or r["revision"]>heads[r["record_id"]]["revision"]:heads[r["record_id"]]=r
        assertions=[r for r in heads.values() if r["scope"]["episode_id"]==episode_id];own={oid:o for oid,o in obs.items() if any(u["episode_id"]==episode_id for u in o["ranges"])}
        status="immature";reason="UNRESOLVED_FINALITY";complete=None
        if any(r["authority_id"] is None for r in assertions):status="invalid";reason="INVALID_ASSERTION_AUTHORITY"
        elif ep["exit"] is None:status="open";reason="OPEN_EPISODE"
        elif any(x["instrument_id"]==ep["instrument"] for x in self._coverage(visible,as_of_us)):reason="UNRESOLVED_SNAPSHOT_COVERAGE"
        elif any(o["T"] is None for o in own.values()):reason="UNKNOWN_OBLIGATION_TOTAL"
        elif any(o["T"]!=o["B"] for o in own.values()):reason="UNSETTLED_OBLIGATION"
        else:
            wanted_o={(oid,o["revision"]) for oid,o in own.items()};wanted_p={(p["record_id"],1) for o in own.values() for p in o["postings"]}
            found_o={(x["obligation_id"],x["revision"]) for r in assertions for x in r["obligation_revision_refs"]};found_p={(x["posting_id"],x["revision"]) for r in assertions for x in r["posting_refs"]}
            kinds={"fill","fee"}|({"funding"} if any(o["kind"]=="funding" for o in own.values()) else set())|({"posting"} if wanted_p else set())
            covered=True
            for kind in kinds:
                end=ep["entry"]
                intervals=sorted((r["scope"]["economic_from_us"],r["scope"]["economic_to_exclusive_us"]) for r in assertions if kind in r["scope"]["event_kinds"])
                for a,b in intervals:
                    if a<=end:end=max(end,b)
                if end<=ep["exit"]:covered=False
            if assertions and covered and wanted_o==found_o and wanted_p==found_p:
                status="complete";reason=None
                times=[ep["exit"]]+[r["available_at_us"] for r in assertions]
                times += [o["available"] for o in own.values()]+[p["available_at_us"] for o in own.values() for p in o["postings"]]
                times += [f["record"]["available_at_us"] for f in inv["fills"].values() if any(u["episode_id"]==episode_id for u in inv["origins"][f["record"]["fee_obligation_id"]]["ranges"])]
                complete=max(times)
        nr={}
        if ep["exit"] is None:nr["natural_exit_at_us"]="OPEN_EPISODE"
        if complete is None:nr["complete_at_us"]=reason
        return deepcopy(dict(episode_id=episode_id,as_of_us=as_of_us,natural_exit_at_us=ep["exit"],status=status,complete_at_us=complete,assertion_refs=sorted([_key(r) for r in assertions],key=_bytes),blocking_reasons=[] if reason is None else [reason],null_reasons=nr))

    def audit(self):
        state=dict(config=self._config,records=sorted(self._records.values(),key=_identity),derived_entries=self._entries,corroborating_source_refs=self._corroborating)
        return deepcopy(dict(namespace=NS,schema_version=1,profile=PROFILE,ledger_id=self._config["ledger_id"],config_sha256=_digest(self._config),source_manifest_sha256=self._manifest_hash,
            committed_sha256=_digest(state),committed_state=state,integrity="stopped" if self._failures else "clean",failure_receipts=self._failures))

"""Conditional native warmup/feature diagnostics, without replay or fitting."""
import argparse
import json
from pathlib import Path

from research.qr004.validate_history import native_warmup, sha256
from research.qr005.validate_history import demand, validate_dataset


def assess(root, base_root, spec_path, fixture_path):
    root = Path(root)
    spec = json.loads(Path(spec_path).read_text())
    fixture = json.loads(Path(fixture_path).read_text())
    qr_root = Path(__file__).resolve().parents[2]
    for name, digest in fixture["source_sha256"].items():
        demand(sha256(qr_root/name) == digest, "native source changed: "+name)
    validation = validate_dataset(root, base_root, spec_path)
    manifest = json.loads((root/"manifest.json").read_text())
    import numpy as np
    import pandas as pd
    from src.config import SystematicConfig
    from src.crypto_ml import causal_features

    assets = {}
    for symbol in spec["scope"]["symbols"]:
        frames = {}
        for item in manifest["files"]:
            if item["symbol"] == symbol:
                key = {0: "funding", 3600: "1h", 14400: "4h", 86400: "1d"}[item["interval_seconds"]]
                frames[key] = pd.read_csv(root/item["path"])
        cfg = SystematicConfig.build(fixture["instruments"][symbol]["fixture"]["strategy_config"])
        demand(not cfg.ml_model_path, "model loading is not allowed")
        start = spec["calendar"]["baseline_start"]
        # Declared diagnostic constant only; never infer historical truth from
        # metadata or from the dataset funding descriptor interval_seconds=0.
        warmup = native_warmup(frames, cfg, start, funding_interval=28800)
        features = causal_features(frames["1h"])
        selected = features.loc[frames["1h"].timestamp+3600 >= start]
        assets[symbol] = {"warmup": warmup,
            "closed_hour_feature_rows_from_start": len(selected),
            "feature_columns": list(selected.columns),
            "all_features_finite": bool(np.isfinite(selected.to_numpy()).all()),
            "nonconstant_features": [name for name in selected if selected[name].nunique() > 1],
            "fitting_performed": False, "new_position_labels": 0}
    return {"schema_version": 1, "manifest_sha256": sha256(root/"manifest.json"),
        "data_status": validation["data_status"], "native_fixture_sha256": sha256(fixture_path),
        "native_source_sha256": fixture["source_sha256"], "assets": assets,
        "baseline_replays": 0, "model_fits": 0, "training_status": "NOT_READY",
        "limitation": "Native warmup assumes constant 28800s annualization for computation only; G3 cashflow policy remains blocked. Indicator and causal-feature calculation is not a trained scaler or model."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--base-root", required=True)
    parser.add_argument("--spec", default="research/qr005/data-acceptance.json")
    parser.add_argument("--fixture", default="research/qr003/results/phase-a-input-spec.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    path = Path(args.output)
    demand(not path.exists(), "diagnostic output exists")
    result = assess(args.root, args.base_root, args.spec, args.fixture)
    with path.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()

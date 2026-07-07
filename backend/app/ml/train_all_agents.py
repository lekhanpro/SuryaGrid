"""Phase 1.7 - train every agent honestly, in one command.

    python -m app.ml.train_all_agents --region bengaluru --data-mode real

Behaviour:
  * In --data-mode real, no synthetic fallback is permitted (enforced by the dataset
    builder and by each trainer skipping when real data is insufficient).
  * If the ML datasets are missing, they are built first (unless --no-build).
  * Each agent is trained OR skipped honestly; a training-run manifest and a per-agent
    summary are written and printed.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime

from app.ml import provenance as prov
from app.ml import (
    train_cloud_agent,
    train_dsm_agent,
    train_load_agent,
    train_rl_agent,
    train_solar_agent,
)
from app.ml.build_ml_datasets import F_WEATHER, build_all

AGENTS = [
    ("solar", train_solar_agent.train),
    ("cloud", train_cloud_agent.train),
    ("dsm", train_dsm_agent.train),
    ("load", train_load_agent.train),
    ("rl", train_rl_agent.train),
]


def run(
    region: str,
    data_mode: str,
    start_year: int,
    end_year: int,
    do_build: bool,
    allow_build: bool = True,
) -> dict:
    if data_mode not in (prov.DATA_MODE_REAL, prov.DATA_MODE_DEMO):
        raise ValueError("data-mode must be 'real' or 'demo'")

    prov.ensure_dirs()
    datasets_present = prov.ml_file_exists(F_WEATHER)
    if allow_build and (do_build or not datasets_present):
        print(
            f"[train_all_agents] Building datasets first (present={datasets_present}, "
            f"do_build={do_build})"
        )
        build_all(region, data_mode, start_year, end_year)
    elif not datasets_present:
        print(
            "[train_all_agents] WARNING: datasets missing and --no-build set; "
            "agents will skip honestly."
        )
    elif data_mode == prov.DATA_MODE_REAL:
        print("[train_all_agents] Using existing real datasets in backend/data/ml/.")

    results: dict[str, dict] = {}
    for name, fn in AGENTS:
        print(f"\n[train_all_agents] === training agent: {name} ===")
        try:
            results[name] = fn(data_mode)
        except prov.SyntheticFallbackError as exc:
            results[name] = {"agent": name, "status": "ABORTED_REAL_MODE", "reason": str(exc)}
        except Exception as exc:  # noqa: BLE001 - one agent failing must not kill the run
            results[name] = {"agent": name, "status": "ERROR", "reason": repr(exc)}
            print(f"[train_all_agents] ERROR training {name}: {exc!r}")

    trained = [n for n, r in results.items() if r.get("status", "").startswith("TRAINED")]
    skipped = [n for n, r in results.items() if r.get("status") in ("SKIPPED", "ABORTED_REAL_MODE")]
    errored = [n for n, r in results.items() if r.get("status") == "ERROR"]

    manifest = {
        "region": region,
        "data_mode": data_mode,
        "trained_at": datetime.now(UTC).isoformat(),
        "trained_agents": trained,
        "skipped_agents": skipped,
        "errored_agents": errored,
        "results": results,
    }
    path = prov.model_metadata_dir() / "training_run_manifest.json"
    prov.save_json(manifest, path)

    print("\n[train_all_agents] ===== SUMMARY =====")
    for name, r in results.items():
        line = f"  {name:6s}: {r.get('status')}"
        if r.get("metrics"):
            m = r["metrics"]
            line += f"  {{r2/f1: {m.get('r2', m.get('f1'))}}}"
        if r.get("production_ready") is not None:
            line += f"  production_ready={r.get('production_ready')}"
        print(line)
    print(f"[train_all_agents] trained={trained} skipped={skipped} errored={errored}")
    print(f"[train_all_agents] manifest -> {path}")
    return manifest


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Train all Phase 1.7 agents.")
    p.add_argument("--region", default="bengaluru")
    p.add_argument("--data-mode", default="real", choices=["real", "demo"])
    p.add_argument("--start-year", type=int, default=2022)
    p.add_argument("--end-year", type=int, default=2024)
    p.add_argument("--build", action="store_true", help="Force rebuild datasets first")
    p.add_argument("--no-build", action="store_true", help="Never build; require existing datasets")
    args = p.parse_args(argv if argv is not None else sys.argv[1:])

    do_build = args.build and not args.no_build
    try:
        run(
            args.region,
            args.data_mode,
            args.start_year,
            args.end_year,
            do_build,
            allow_build=not args.no_build,
        )
    except prov.SyntheticFallbackError as exc:
        print(f"[train_all_agents] REAL-MODE ABORT: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

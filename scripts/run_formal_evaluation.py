#!/usr/bin/env python3
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


DEFAULT_MATRIX = "50:10,100:20,250:40,500:80,1000:120"


def parse_matrix(value):
    cases = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        users, threads = item.split(":")
        cases.append((int(users), int(threads)))
    return cases


def main():
    repo_root = Path(__file__).resolve().parents[1]
    matrix = parse_matrix(os.getenv("EVAL_MATRIX", DEFAULT_MATRIX))
    evaluation_id = os.getenv("EVAL_ID", datetime.now().strftime("%Y%m%d_%H%M%S"))
    evidence_root = repo_root / os.getenv("EVIDENCE_DIR", "evaluation_results")
    evidence_root.mkdir(parents=True, exist_ok=True)

    print(f"[Eval] Evaluation id: {evaluation_id}")
    print(f"[Eval] Cases: {matrix}")

    results = []

    for users, threads in matrix:
        run_id = f"{evaluation_id}_users{users}_threads{threads}"
        run_dir = evidence_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        log_path = run_dir / "console.log"

        env = os.environ.copy()
        env.update({
            "RUN_ID": run_id,
            "NUM_USERS": str(users),
            "LOAD_TEST_THREADS": str(threads),
            "EVIDENCE_DIR": str(evidence_root),
        })

        print(f"[Eval] Running {run_id}")
        with open(log_path, "w") as log_file:
            process = subprocess.run(
                [sys.executable, "main.py"],
                cwd=repo_root,
                env=env,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
            )

        status = "PASS" if process.returncode == 0 else "FAIL"
        results.append((run_id, status, process.returncode, str(log_path)))
        print(f"[Eval] {run_id}: {status} ({log_path})")

        if process.returncode != 0 and os.getenv("EVAL_STOP_ON_FAIL", "true").lower() in {"1", "true", "yes"}:
            break

    summary_path = evidence_root / f"{evaluation_id}_summary.csv"
    with open(summary_path, "w") as f:
        f.write("run_id,status,return_code,console_log\n")
        for run_id, status, return_code, log_path in results:
            f.write(f"{run_id},{status},{return_code},{log_path}\n")

    print(f"[Eval] Summary: {summary_path}")


if __name__ == "__main__":
    main()

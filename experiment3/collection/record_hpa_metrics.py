import csv
import json
import subprocess
import time
from datetime import datetime

# ============================================================
# Experiment 3 - Kubernetes HPA Metrics Recorder
# ============================================================

OUTPUT_FILE = "experiment3_final_mixed.csv"
INTERVAL_SECONDS = 10
HPA_NAME = "php-apache"


def get_hpa():
    """Retrieve the current HPA state from Kubernetes."""

    result = subprocess.run(
        [
            "kubectl",
            "get",
            "hpa",
            HPA_NAME,
            "-o",
            "json",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return json.loads(result.stdout)


# Line-buffered file + explicit flush provides additional
# protection for a long-running experiment.
with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8",
    buffering=1,
) as file:

    writer = csv.writer(file)

    writer.writerow(
        [
            "timestamp",
            "current_replicas",
            "desired_replicas",
            "current_cpu_percentage",
            "target_cpu_percentage",
        ]
    )

    file.flush()

    print("=" * 60)
    print("Experiment 3 HPA Metrics Recorder")
    print("=" * 60)
    print(f"Output file: {OUTPUT_FILE}")
    print(f"Sampling interval: ~{INTERVAL_SECONDS} seconds")
    print(f"HPA: {HPA_NAME}")
    print("Press Ctrl+C only after the experiment is finished.")
    print("=" * 60)

    successful_rows = 0
    failed_rows = 0

    try:

        while True:

            loop_start = time.monotonic()

            timestamp = datetime.now().astimezone().isoformat(
                timespec="seconds"
            )

            try:

                hpa = get_hpa()

                # ------------------------------------------------
                # Current and desired replicas
                # ------------------------------------------------

                status = hpa.get("status", {})

                current_replicas = status.get(
                    "currentReplicas",
                    "",
                )

                desired_replicas = status.get(
                    "desiredReplicas",
                    "",
                )

                # ------------------------------------------------
                # Current CPU utilisation
                # ------------------------------------------------

                current_cpu = ""

                for metric in status.get(
                    "currentMetrics",
                    [],
                ):

                    if (
                        metric.get("type") == "Resource"
                        and metric.get("resource", {}).get("name")
                        == "cpu"
                    ):

                        current_cpu = (
                            metric.get("resource", {})
                            .get("current", {})
                            .get("averageUtilization", "")
                        )

                        break

                # ------------------------------------------------
                # HPA target CPU
                # ------------------------------------------------

                target_cpu = ""

                for metric in (
                    hpa.get("spec", {}).get("metrics", [])
                ):

                    if (
                        metric.get("type") == "Resource"
                        and metric.get("resource", {}).get("name")
                        == "cpu"
                    ):

                        target_cpu = (
                            metric.get("resource", {})
                            .get("target", {})
                            .get("averageUtilization", "")
                        )

                        break

                # ------------------------------------------------
                # Save observation
                # ------------------------------------------------

                writer.writerow(
                    [
                        timestamp,
                        current_replicas,
                        desired_replicas,
                        current_cpu,
                        target_cpu,
                    ]
                )

                # Important for a long experiment:
                # write data to disk immediately.
                file.flush()

                successful_rows += 1

                print(
                    f"{timestamp} | "
                    f"CPU: {current_cpu}% | "
                    f"Current: {current_replicas} | "
                    f"Desired: {desired_replicas} | "
                    f"Rows: {successful_rows}"
                )

            except Exception as error:

                failed_rows += 1

                # Keep a timestamped missing row so that we know
                # a collection attempt occurred.
                writer.writerow(
                    [
                        timestamp,
                        "",
                        "",
                        "",
                        "",
                    ]
                )

                file.flush()

                print(
                    f"{timestamp} | "
                    f"WARNING: metric collection failed | "
                    f"{error}"
                )

            # ----------------------------------------------------
            # Maintain approximately 10-second sampling intervals
            # ----------------------------------------------------

            elapsed = time.monotonic() - loop_start

            remaining = INTERVAL_SECONDS - elapsed

            if remaining > 0:
                time.sleep(remaining)

    except KeyboardInterrupt:

        print()
        print("=" * 60)
        print("Recorder stopped safely.")
        print(f"Successful observations: {successful_rows}")
        print(f"Failed collection attempts: {failed_rows}")
        print(f"Saved to: {OUTPUT_FILE}")
        print("=" * 60)
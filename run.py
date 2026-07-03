from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def start_process(name: str, args: list[str], quiet: bool = False) -> subprocess.Popen:
    if quiet:
        log_path = Path("/tmp") / f"{name}.log"
        log_file = log_path.open("ab")
        return subprocess.Popen(args, cwd=BASE_DIR, stdout=log_file, stderr=subprocess.STDOUT, start_new_session=True)
    print(f"Starting {name}: {' '.join(args)}", flush=True)
    return subprocess.Popen(args, cwd=BASE_DIR)


def terminate_process(name: str, process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    print(f"Stopping {name}...", flush=True)
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        print(f"Force killing {name}...", flush=True)
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run app.py and python-nezha-agent together")
    parser.add_argument("-c", "--config", default="config.yml", help="agent config file path")
    args = parser.parse_args()

    app_process = start_process("app", [sys.executable, "app.py"])
    agent_process = start_process("agent", [sys.executable, "main.py"], quiet=True)
    processes = [("app", app_process), ("agent", agent_process)]
    stopping = False

    def stop(_signum, _frame) -> None:
        nonlocal stopping
        stopping = True
        for name, process in reversed(processes):
            terminate_process(name, process)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    try:
        agent_exit_reported = False
        while not stopping:
            app_code = app_process.poll()
            if app_code is not None:
                print(f"app exited with code {app_code}", flush=True)
                stopping = True
                break

            agent_code = agent_process.poll()
            if agent_code is not None and not agent_exit_reported:
                agent_exit_reported = True
                print(f"agent exited with code {agent_code}; app is still running", flush=True)
                print("agent logs: /tmp/agent.log", flush=True)

            time.sleep(1)
    finally:
        for name, process in reversed(processes):
            terminate_process(name, process)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

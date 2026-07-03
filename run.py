from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

# Set these here or via environment variables. If any required value is empty,
# main.py will not be started.
SERVER = os.environ.get("SERVER", "")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "")
UUID = os.environ.get("UUID", "")
TLS = os.environ.get("TLS", "true")


def agent_enabled() -> bool:
    return bool(SERVER.strip() and CLIENT_SECRET.strip() and UUID.strip())


def agent_env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "SERVER": SERVER,
            "CLIENT_SECRET": CLIENT_SECRET,
            "UUID": UUID,
            "TLS": TLS,
        }
    )
    return env


def start_process(name: str, args: list[str], quiet: bool = False, env: dict[str, str] | None = None) -> subprocess.Popen:
    if quiet:
        log_path = Path("/tmp") / f"{name}.log"
        log_file = log_path.open("ab")
        return subprocess.Popen(args, cwd=BASE_DIR, stdout=log_file, stderr=subprocess.STDOUT, start_new_session=True, env=env)
    print(f"Starting {name}: {' '.join(args)}", flush=True)
    return subprocess.Popen(args, cwd=BASE_DIR, env=env)


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
    app_process = start_process("app", [sys.executable, "app.py"])
    processes = [("app", app_process)]
    agent_process = None
    if agent_enabled():
        agent_process = start_process("agent", [sys.executable, "main.py"], quiet=True, env=agent_env())
        processes.append(("agent", agent_process))
    else:
        print("SERVER, CLIENT_SECRET, or UUID is empty; skip starting main.py", flush=True)

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

            if agent_process is not None:
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

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
DEFAULT_API_URL = "http://127.0.0.1:8000"


def project_python() -> Path:
    candidate = PROJECT_ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return candidate if candidate.exists() else Path(sys.executable)


def frontend_root() -> Path:
    candidates = [path.parent for path in PROJECT_ROOT.glob("*/vite.config.ts")]
    if len(candidates) != 1:
        raise RuntimeError(f"Expected one frontend directory, found {len(candidates)}.")
    return candidates[0]


def api_request(
    path: str,
    *,
    base_url: str = DEFAULT_API_URL,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    token: str | None = None,
    timeout: float = 5,
) -> Any:
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{base_url}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Cannot connect to {base_url}: {error.reason}") from error


def stop_process_tree(process: subprocess.Popen[Any] | None) -> None:
    if process is None or process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def wait_for_backend(process: subprocess.Popen[Any], timeout_seconds: float = 15) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Backend exited early with code {process.returncode}.")
        try:
            health = api_request("/api/health", timeout=1)
            if health.get("status") == "ok":
                return
        except RuntimeError:
            time.sleep(0.5)
    raise RuntimeError("Backend did not start within 15 seconds. Check port 8000.")


def run_dev() -> int:
    python = project_python()
    frontend = frontend_root()
    npm = "npm.cmd" if os.name == "nt" else "npm"
    if not (frontend / "node_modules").exists():
        raise RuntimeError("Frontend dependencies are missing. Run npm install first.")

    process_flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    backend: subprocess.Popen[Any] | None = None
    frontend_process: subprocess.Popen[Any] | None = None
    try:
        backend = subprocess.Popen(
            [str(python), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=BACKEND_ROOT,
            creationflags=process_flags,
        )
        wait_for_backend(backend)
        print("Backend: http://127.0.0.1:8000/docs", flush=True)
        print("Frontend: http://127.0.0.1:8443", flush=True)
        print("Press Ctrl+C or q in Vite to stop.", flush=True)
        frontend_process = subprocess.Popen(
            [npm, "run", "dev"],
            cwd=frontend,
            creationflags=process_flags,
        )
        return frontend_process.wait()
    except KeyboardInterrupt:
        return 130
    finally:
        stop_process_tree(frontend_process)
        stop_process_tree(backend)


def reset_demo() -> int:
    result = subprocess.run(
        [str(project_python()), "-m", "app.seed", "--reset"],
        cwd=BACKEND_ROOT,
        check=False,
    )
    return result.returncode


def smoke_test(base_url: str) -> int:
    health = api_request("/api/health", base_url=base_url)
    if health.get("status") != "ok":
        raise RuntimeError("Invalid health response.")

    login = api_request(
        "/api/auth/login",
        base_url=base_url,
        method="POST",
        body={"username": "kim.jiyeon", "password": "demo"},
    )
    token = login["accessToken"]
    youths = api_request("/api/youths", base_url=base_url, token=token)
    if not youths:
        raise RuntimeError("Youth list is empty.")
    youth_id = youths[0]["youthId"]

    detail = api_request(f"/api/youths/{youth_id}", base_url=base_url, token=token)
    if detail["youth"]["youthId"] != youth_id:
        raise RuntimeError("Youth detail does not match.")

    checkin = api_request(
        "/api/checkins",
        base_url=base_url,
        method="POST",
        token=token,
        body={
            "youthId": youth_id,
            "responseType": "좋아요",
            "responseText": "로컬 Python 스모크 테스트 응답",
            "followUps": ["밥은 잘 챙겨 먹고 있어요"],
        },
    )
    if checkin["checkin"]["youthId"] != youth_id:
        raise RuntimeError("Failed to store a check-in.")

    analysis = api_request(
        f"/api/youths/{youth_id}/analyze",
        base_url=base_url,
        method="POST",
        token=token,
        body={"mode": "rule"},
    )
    if analysis["youthId"] != youth_id:
        raise RuntimeError("Failed to analyze status.")

    action = api_request(
        f"/api/youths/{youth_id}/actions",
        base_url=base_url,
        method="POST",
        token=token,
        body={"status": "관찰지속", "memo": "Python 스모크 테스트 조치"},
    )
    if action["youthId"] != youth_id:
        raise RuntimeError("Failed to store a case action.")

    print("Smoke test passed: health -> login -> list -> detail -> checkin -> analyze -> action")
    print("Run 'python manage.py reset' to restore seed data.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Local launcher for the Jaripdong MVP")
    parser.add_argument("command", nargs="?", choices=["dev", "reset", "smoke"], default="dev")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="API base URL for the smoke command")
    args = parser.parse_args()

    try:
        if args.command == "dev":
            return run_dev()
        if args.command == "reset":
            return reset_demo()
        return smoke_test(args.api_url)
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


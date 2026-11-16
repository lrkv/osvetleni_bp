#!/usr/bin/env python3
"""Verify Linux installation in a temporary copy, without running production backend."""
import argparse
import functools
import http.server
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request


ROUTES = ("/", "/mapa/", "/udalosti/", "/backend-config.json")


def run(command, cwd, env):
    print("\n$ " + " ".join(map(str, command)), flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def check_http(port):
    for route in ROUTES:
        url = f"http://127.0.0.1:{port}{route}"
        with urllib.request.urlopen(url, timeout=5) as response:
            if response.status != 200 or not response.read():
                raise RuntimeError(f"Neplatná odpověď: {url}")
        print("HTTP OK:", route, flush=True)


def verify_static(frontend):
    public = frontend / ".output" / "public"
    for relative in ("index.html", "mapa/index.html", "udalosti/index.html", "backend-config.json"):
        if not (public / relative).is_file():
            raise RuntimeError(f"Chybí generovaný soubor: {relative}")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(public))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        check_http(server.server_port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def verify_node(frontend, env):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    server_env = {**env, "NODE_ENV": "production", "HOST": "127.0.0.1", "PORT": str(port)}
    process = subprocess.Popen(["node", ".output/server/index.mjs"], cwd=frontend, env=server_env)
    try:
        deadline = time.monotonic() + 60
        while True:
            if process.poll() is not None:
                raise RuntimeError("Frontendový Node.js server neočekávaně skončil.")
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2):
                    break
            except (urllib.error.URLError, TimeoutError):
                if time.monotonic() >= deadline:
                    raise RuntimeError("Frontendový Node.js server nenaběhl do 60 sekund.")
                time.sleep(.2)
        check_http(port)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-arm64", action="store_true", help="Vyžadovat Linux ARM64 jako na 64bit Raspberry Pi.")
    args = parser.parse_args()
    if platform.system() != "Linux":
        raise RuntimeError("Tento test se musí spustit na Linuxu; jiný systém jeho běh neověří.")
    if sys.version_info < (3, 11):
        raise RuntimeError("Je potřeba Python 3.11 nebo novější.")
    if args.require_arm64 and platform.machine().lower() not in ("aarch64", "arm64"):
        raise RuntimeError(f"Očekáván ARM64, aktuální architektura: {platform.machine()}")
    for executable in ("node", "npm"):
        if shutil.which(executable) is None:
            raise RuntimeError(f"Chybí příkaz {executable} v PATH.")
    print("Systém:", platform.platform(), flush=True)
    print("Architektura:", platform.machine(), flush=True)
    print("Python:", sys.version, flush=True)
    source = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["NO_PROXY"] = "127.0.0.1,localhost"
    env["no_proxy"] = env["NO_PROXY"]
    # Test an actual development install, regardless of the caller's production env.
    env.pop("NODE_ENV", None)
    env.pop("PYTHONPATH", None)
    run(["node", "--version"], source, env)
    run(["npm", "--version"], source, env)
    with tempfile.TemporaryDirectory(prefix="osvetleni-linux-") as folder:
        work = Path(folder)
        ignored = shutil.ignore_patterns("node_modules", ".output", ".nuxt", ".nitro", ".cache", ".data", "__pycache__", ".venv", ".git")
        for name in ("backend", "frontend"):
            shutil.copytree(source / name, work / name, ignore=ignored)
        python = work / ".venv" / "bin" / "python"
        run([sys.executable, "-m", "venv", str(work / ".venv")], work, env)
        run([str(python), "-m", "pip", "install", "-r", "backend/requirements-dev.txt"], work, env)
        # Unit/integration tests connect only to their fake local peers.
        run([str(python), "-B", "-m", "unittest", "discover", "-s", "backend/tests", "-v"], work, env)
        frontend = work / "frontend"
        run(["npm", "ci", "--include=dev", "--include=optional"], frontend, env)
        run(["node", "--test", "tests/lighting.test.mjs", "tests/eventGroups.test.mjs"], frontend, env)
        run(["npm", "run", "generate"], frontend, env)
        verify_static(frontend)
        run(["npm", "run", "build"], frontend, env)
        verify_node(frontend, env)
    print("\nOK: Linux instalace, testy, statické generování i spuštění frontendového serveru prošly.", flush=True)
    print("Připojení skutečného MTB a hJOP nebylo součástí testu.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError, OSError) as error:
        print(f"\nOVĚŘENÍ SELHALO: {error}", file=sys.stderr, flush=True)
        sys.exit(1)

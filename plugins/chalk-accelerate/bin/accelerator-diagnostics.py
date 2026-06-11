#!/usr/bin/env python3
"""Check whether the Chalk resolvers in a project can be statically accelerated.

Exports the current Chalk project to a graph proto, sends it to the Chalk static
accelerator service, and prints any acceleration diagnostics in a
``file:line: severity: message`` format.

Exit codes:
  0 - every resolver is statically accelerable
  1 - one or more resolvers produced acceleration diagnostics
  2 - the check itself failed (export error, network error, bad response, ...)

The accelerator host is resolved from, in order: ``--host``, the
``CHALK_ACCELERATOR_HOST`` environment variable, and the default
``https://accelerator.chalk.ai``. If ``CHALK_ACCELERATOR_TOKEN`` is set it is
sent as a bearer token.

Run this script with the same Python environment that the Chalk project uses
(it must be able to ``import chalk``).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_HOST = "https://accelerator.chalk.ai"
DIAGNOSTICS_RPC = "/chalk.staticaccelerator.v1.StaticAcceleratorService/GetStaticConversionDiagnostics"

SEVERITY_NAMES = {
    0: "diagnostic",
    1: "error",
    2: "warning",
    3: "info",
    4: "hint",
}


def find_project_root(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "chalk.yaml").is_file() or (candidate / "chalk.yml").is_file():
            return candidate
    return None


def resolve_host(cli_host: str | None) -> str:
    host = cli_host or os.environ.get("CHALK_ACCELERATOR_HOST") or DEFAULT_HOST
    if "://" not in host:
        host = f"https://{host}"
    return host.rstrip("/")


def export_project(project_root: Path) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".pb", delete=False) as tmp:
        export_path = Path(tmp.name)
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "chalk.cli",
                "export",
                str(export_path),
                "--proto",
                "--include-captured-global-values",
            ],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            sys.stderr.write(result.stdout)
            sys.stderr.write(result.stderr)
            raise RuntimeError(
                f"'python -m chalk.cli export' failed with exit code {result.returncode}"
            )
        return export_path.read_bytes()
    finally:
        export_path.unlink(missing_ok=True)


def encode_varint(value: int) -> bytes:
    out = bytearray()
    while True:
        bits = value & 0x7F
        value >>= 7
        if value:
            out.append(bits | 0x80)
        else:
            out.append(bits)
            return bytes(out)


def build_request_bytes(export_bytes: bytes) -> bytes:
    """Serialize a GetStaticConversionDiagnosticsRequest.

    ``export`` is field 2 (length-delimited) and ``render_failed_proofs`` is field 3
    (varint). Framed by hand so this script works even when the installed chalkpy
    predates the staticaccelerator protos.
    """
    return b"\x12" + encode_varint(len(export_bytes)) + export_bytes + b"\x18\x01"


def post_diagnostics(host: str, request_bytes: bytes, timeout: float) -> bytes:
    headers = {
        "content-type": "application/proto",
        "connect-protocol-version": "1",
    }
    token = os.environ.get("CHALK_ACCELERATOR_TOKEN")
    if token:
        headers["authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        host + DIAGNOSTICS_RPC,
        data=request_bytes,
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def print_diagnostics(response_bytes: bytes, project_root: Path) -> int:
    try:
        from chalk._gen.chalk.artifacts.v1 import export_pb2
    except ImportError as error:
        raise RuntimeError(
            "could not import chalkpy protos to decode the response; run this script with "
            f"the project's Python environment ({error})"
        ) from error

    export = export_pb2.Export()
    export.ParseFromString(response_bytes)

    failed_imports = list(getattr(export, "failed", ()))
    for failure in failed_imports:
        location = failure.file_name or "<project>"
        print(f"{location}: error: project import failed during export:\n{failure.traceback}")

    count = 0
    for params in export.lsp.diagnostics:
        try:
            uri = str(Path(params.uri).relative_to(project_root))
        except ValueError:
            uri = params.uri
        for diagnostic in params.diagnostics:
            count += 1
            severity = SEVERITY_NAMES.get(diagnostic.severity, str(diagnostic.severity))
            line = diagnostic.range.start.line + 1  # LSP lines are 0-based
            print(f"{uri}:{line}: {severity}: {diagnostic.message}\n")

    if failed_imports:
        return 2
    if count:
        print(f"{count} resolver(s) cannot be statically accelerated.")
        return 1
    print("All resolvers are statically accelerable.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--host",
        help=f"Accelerator service host (default: $CHALK_ACCELERATOR_HOST or {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Path inside the Chalk project to check (default: current directory)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Request timeout in seconds (default: 120)",
    )
    args = parser.parse_args()

    project_root = find_project_root(args.project)
    if project_root is None:
        print(
            f"error: no chalk.yaml/chalk.yml found at or above '{args.project}'; "
            "run from inside a Chalk project or pass --project",
            file=sys.stderr,
        )
        return 2

    host = resolve_host(args.host)

    try:
        export_bytes = export_project(project_root)
        response_bytes = post_diagnostics(host, build_request_bytes(export_bytes), args.timeout)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        print(f"error: accelerator service at {host} returned HTTP {error.code}: {body}", file=sys.stderr)
        return 2
    except (urllib.error.URLError, OSError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    return print_diagnostics(response_bytes, project_root)


if __name__ == "__main__":
    sys.exit(main())

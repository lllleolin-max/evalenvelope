"""CLI: local JSON files only. No model calls or external release actions."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from . import Error, parse_manifest, parse_state, empty_state, import_observations, envelope, plan, check_envelope, check_plan


def read(path):
    p = Path(path)
    if p.stat().st_size > 4*1024*1024:
        raise Error("JSON input exceeds 4 MiB")
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise Error("duplicate JSON object key: " + key)
            result[key] = value
        return result

    def invalid_constant(value):
        raise Error("nonfinite JSON constant: " + value)

    def source_integer(value):
        if len(value) > 128:
            raise Error("JSON source integer exceeds 128-character literal bound")
        return int(value)

    try:
        return json.loads(p.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs,
                          parse_constant=invalid_constant, parse_int=source_integer)
    except RecursionError as exc:
        raise Error("JSON nesting exceeds parser resource limit") from exc


def output(value, path):
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    encoded = payload.encode("utf-8")
    if len(encoded) > 4*1024*1024:
        raise Error("JSON output exceeds 4 MiB; destination is unchanged")
    if path is None:
        stream = getattr(sys.stdout, "buffer", None)
        if stream is None:
            raise Error("stdout requires a binary buffer for stable UTF-8 output")
        stream.write(encoded)
        stream.flush()
        return
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=dest.parent, delete=False) as handle:
            tmp = handle.name
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, dest)
    finally:
        if tmp is not None and Path(tmp).exists():
            Path(tmp).unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Finite paired benchmark completion envelopes (no population CI)")
    parser.add_argument("command", choices=("init", "analyze", "plan", "import", "check"))
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--state")
    parser.add_argument("--margin", default="0")
    parser.add_argument("--options")
    parser.add_argument("--observations")
    parser.add_argument("--frozen-plan")
    parser.add_argument("--certificate")
    parser.add_argument("--prove-optimal", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        manifest = parse_manifest(read(args.manifest))
        state = parse_state(manifest, read(args.state)) if args.state else empty_state(manifest)
        if args.command == "init":
            result = empty_state(manifest).data()
        elif args.command == "analyze":
            result = envelope(manifest, state, args.margin)
        elif args.command == "plan":
            if not args.options:
                raise Error("plan requires --options")
            result = plan(manifest, state, read(args.options))
        elif args.command == "import":
            if not args.observations:
                raise Error("import requires --observations")
            frozen = read(args.frozen_plan) if args.frozen_plan else None
            result = import_observations(manifest, state, read(args.observations), frozen).data()
        else:
            if not args.certificate:
                raise Error("check requires --certificate")
            certificate = read(args.certificate)
            if not isinstance(certificate, dict):
                raise Error("certificate must be a JSON object")
            result = check_envelope(manifest, state, certificate) if certificate.get("kind") == "completion_certificate" else check_plan(manifest, state, certificate, args.prove_optimal)
        output(result, args.output)
        return 0
    except (Error, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

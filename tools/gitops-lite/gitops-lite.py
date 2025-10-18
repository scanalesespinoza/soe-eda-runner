#!/usr/bin/env python3
"""Lightweight GitOps utility for kubectl + kustomize workflows."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional

try:
    import yaml  # type: ignore
except ImportError as exc:  # pragma: no cover - dependency missing
    raise SystemExit("PyYAML is required: pip install pyyaml") from exc

REQUIRED_LABELS = {
    "app.kubernetes.io/part-of": "soe-eda-runner",
    "gitops-lite": "managed",
}


class KubectlRunner:
    """Helper to execute kubectl commands with shared flags."""

    def __init__(self, kube_bin: str, context: Optional[str], kubeconfig: Optional[str]):
        self._base_cmd: List[str] = [kube_bin]
        if kubeconfig:
            self._base_cmd.extend(["--kubeconfig", kubeconfig])
        if context:
            self._base_cmd.extend(["--context", context])

    def run(
        self,
        args: Iterable[str],
        *,
        input_data: Optional[str] = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        cmd = self._base_cmd + list(args)
        proc = subprocess.run(
            cmd,
            input=input_data,
            text=True,
            capture_output=True,
        )
        if check and proc.returncode != 0:
            if proc.stdout:
                print(proc.stdout, end="")
            if proc.stderr:
                print(proc.stderr, file=sys.stderr, end="")
            raise SystemExit(proc.returncode)
        return proc


def read_file(path: Path) -> str:
    try:
        return path.read_text()
    except FileNotFoundError as exc:
        raise SystemExit(f"Path not found: {path}") from exc


def render_manifests(path: Path, use_kustomize: bool) -> str:
    if use_kustomize:
        kustomize_bin = os.environ.get("KUSTOMIZE_BIN", "kustomize")
        cmd = [kustomize_bin, "build", str(path)]
        try:
            proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
        except FileNotFoundError as exc:  # pragma: no cover
            raise SystemExit(f"Unable to find kustomize executable '{kustomize_bin}'") from exc
        except subprocess.CalledProcessError as exc:
            sys.stderr.write(exc.stderr)
            raise SystemExit(exc.returncode)
        return proc.stdout

    if path.is_dir():
        manifests = []
        for file_path in sorted(path.glob("*.y*ml")):
            manifests.append(read_file(file_path))
        if not manifests:
            raise SystemExit(f"No manifest files found in directory: {path}")
        return "\n---\n".join(manifests)

    return read_file(path)


def build_apply_args(args: argparse.Namespace, *, prune: bool) -> List[str]:
    apply_args = ["apply", "-f", "-"]
    if args.server_side:
        apply_args.append("--server-side")
    if prune:
        if not args.selector:
            raise SystemExit("Prune operations require --selector")
        apply_args.extend(["--prune", "-l", args.selector])
    return apply_args


def apply_manifest(
    kubectl: KubectlRunner,
    manifest: str,
    args: argparse.Namespace,
    *,
    prune: bool,
) -> None:
    proc = kubectl.run(build_apply_args(args, prune=prune), input_data=manifest, check=False)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def prune_manifest(kubectl: KubectlRunner, manifest: str, args: argparse.Namespace) -> None:
    proc = kubectl.run(
        build_apply_args(args, prune=True), input_data=manifest, check=False
    )
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def run_plan(kubectl: KubectlRunner, manifest: str) -> int:
    proc = kubectl.run(["diff", "-f", "-"], input_data=manifest, check=False)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")
    return proc.returncode


def summarize_status(kubectl: KubectlRunner, manifest_docs: Iterable[dict]) -> None:
    resources = [doc for doc in manifest_docs if isinstance(doc, dict) and doc.get("kind")]
    if not resources:
        print("No Kubernetes resources detected in manifest.")
        return

    status_counts = {"Added": 0, "Changed": 0, "Same": 0}

    for resource in resources:
        metadata = resource.get("metadata", {})
        name = metadata.get("name")
        namespace = metadata.get("namespace")
        kind = resource.get("kind")
        if not name or not kind:
            continue

        yaml_payload = yaml.safe_dump(resource, sort_keys=False)
        diff_proc = kubectl.run(["diff", "-f", "-"], input_data=yaml_payload, check=False)
        if diff_proc.returncode not in (0, 1):
            if diff_proc.stderr:
                print(diff_proc.stderr, file=sys.stderr, end="")
            raise SystemExit(diff_proc.returncode)
        exists = False
        if namespace:
            get_args = ["get", kind, name, "-n", namespace]
        else:
            get_args = ["get", kind, name]
        get_proc = kubectl.run(get_args, check=False)
        if get_proc.returncode not in (0, 1):
            if get_proc.stderr:
                print(get_proc.stderr, file=sys.stderr, end="")
            raise SystemExit(get_proc.returncode)
        exists = get_proc.returncode == 0

        if diff_proc.returncode == 0 and exists:
            status = "Same"
        elif not exists:
            status = "Added"
        else:
            status = "Changed"
        status_counts[status] += 1
        ns_prefix = f"{namespace}/" if namespace else ""
        print(f"{kind}/{ns_prefix}{name}: {status}")

    summary = ", ".join(f"{key}={value}" for key, value in status_counts.items())
    print(f"Summary: {summary}")


def validate_labels(manifest_docs: Iterable[dict]) -> List[str]:
    errors: List[str] = []
    for doc in manifest_docs:
        if not isinstance(doc, dict):
            continue
        metadata = doc.get("metadata") or {}
        name = metadata.get("name", "<unknown>")
        labels = metadata.get("labels") or {}
        for key, expected in REQUIRED_LABELS.items():
            value = labels.get(key)
            if value != expected:
                errors.append(
                    f"Resource '{metadata.get('namespace', 'cluster')}/{name}' missing label {key}={expected}"
                )
    return errors


def cmd_render(args: argparse.Namespace) -> None:
    manifest = render_manifests(Path(args.path), args.kustomize)
    print(manifest, end="")


def cmd_plan(args: argparse.Namespace) -> None:
    manifest = render_manifests(Path(args.path), args.kustomize)
    kubectl = KubectlRunner(args.kube_bin, args.context, args.kubeconfig)
    exit_code = run_plan(kubectl, manifest)
    if exit_code not in (0, 1):
        raise SystemExit(exit_code)


def cmd_status(args: argparse.Namespace) -> None:
    manifest = render_manifests(Path(args.path), args.kustomize)
    docs = list(yaml.safe_load_all(manifest))
    kubectl = KubectlRunner(args.kube_bin, args.context, args.kubeconfig)
    summarize_status(kubectl, docs)


def cmd_apply(args: argparse.Namespace) -> None:
    manifest = render_manifests(Path(args.path), args.kustomize)
    kubectl = KubectlRunner(args.kube_bin, args.context, args.kubeconfig)
    apply_manifest(kubectl, manifest, args, prune=args.enable_prune)


def cmd_prune(args: argparse.Namespace) -> None:
    manifest = render_manifests(Path(args.path), args.kustomize)
    kubectl = KubectlRunner(args.kube_bin, args.context, args.kubeconfig)
    prune_manifest(kubectl, manifest, args)


def cmd_sync(args: argparse.Namespace) -> None:
    manifest = render_manifests(Path(args.path), args.kustomize)
    kubectl = KubectlRunner(args.kube_bin, args.context, args.kubeconfig)
    apply_manifest(kubectl, manifest, args, prune=False)
    if args.enable_prune:
        prune_manifest(kubectl, manifest, args)


def cmd_validate(args: argparse.Namespace) -> None:
    manifest = render_manifests(Path(args.path), args.kustomize)
    docs = list(yaml.safe_load_all(manifest))
    label_errors = validate_labels(docs)
    if label_errors:
        for err in label_errors:
            print(err, file=sys.stderr)
        raise SystemExit(1)

    kubectl = KubectlRunner(args.kube_bin, args.context, args.kubeconfig)
    proc = kubectl.run(["apply", "--dry-run=server", "-f", "-"], input_data=manifest, check=False)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--path", required=True, help="Path to manifest file or kustomize root")
    parser.add_argument(
        "--kustomize",
        action="store_true",
        help="Render the path using 'kustomize build' before acting",
    )
    parser.add_argument("--server-side", action="store_true", dest="server_side")
    parser.add_argument("--enable-prune", action="store_true", dest="enable_prune")
    parser.add_argument("--selector", help="Label selector used for prune operations")
    parser.add_argument("--context", help="Kubeconfig context to use")
    parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    parser.add_argument(
        "--kube-bin",
        default=os.environ.get("KUBE_BIN", "kubectl"),
        help="kubectl compatible binary to use",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="gitops-lite helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_parser = subparsers.add_parser("render", help="Render manifests")
    add_common_arguments(render_parser)
    render_parser.set_defaults(func=cmd_render)

    status_parser = subparsers.add_parser("status", help="Show resource status vs cluster")
    add_common_arguments(status_parser)
    status_parser.set_defaults(func=cmd_status)

    plan_parser = subparsers.add_parser("plan", help="Show diff between repo and cluster")
    add_common_arguments(plan_parser)
    plan_parser.set_defaults(func=cmd_plan)

    apply_parser = subparsers.add_parser("apply", help="Apply manifests")
    add_common_arguments(apply_parser)
    apply_parser.set_defaults(func=cmd_apply)

    prune_parser = subparsers.add_parser("prune", help="Prune managed resources")
    add_common_arguments(prune_parser)
    prune_parser.set_defaults(func=cmd_prune)

    sync_parser = subparsers.add_parser("sync", help="Apply manifests and optionally prune")
    add_common_arguments(sync_parser)
    sync_parser.set_defaults(func=cmd_sync)

    validate_parser = subparsers.add_parser("validate", help="Validate manifests and labels")
    add_common_arguments(validate_parser)
    validate_parser.set_defaults(func=cmd_validate)

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import inspect

try:
    import click
except ModuleNotFoundError:  # pragma: no cover - click is an indirect dependency of typer
    click = None  # type: ignore[assignment]

try:
    import typer
except ModuleNotFoundError as exc:  # pragma: no cover - defensive guard
    requirements = Path(__file__).with_name("requirements.txt")
    install_hint = (
        f"python3 -m pip install -r {requirements}"
        if requirements.exists()
        else "python3 -m pip install typer"
    )
    sys.stderr.write(
        "Falta la dependencia opcional 'typer' requerida por soectl.\n"
        f"Ejecuta: {install_hint}\n"
    )
    raise SystemExit(1) from exc
import yaml  # noqa: F401  # reservado para futuras lecturas de config
from dotenv import load_dotenv
from rich.console import Console

if click is not None:  # pragma: no branch - simple compatibility shim
    signature = inspect.signature(click.Parameter.make_metavar)
    if len(signature.parameters) == 2:
        original_make_metavar = click.Parameter.make_metavar

        def _patched_make_metavar(self, ctx=None):  # type: ignore[override]
            if ctx is None:
                ctx = click.Context(click.Command(self.name or ""))
            return original_make_metavar(self, ctx)

        click.Parameter.make_metavar = _patched_make_metavar  # type: ignore[assignment]

app = typer.Typer(help="SOE EDA Runner - utilitario de instalación y operación")
console = Console()
ROOT = Path(__file__).resolve().parents[2]
GITOPS = ROOT / "tools" / "gitops-lite" / "gitops-lite.py"


def run(cmd, check=True, env=None, input=None):
    """Ejecuta un comando y gestiona errores con salida rica."""
    result = subprocess.run(cmd, text=True, capture_output=True, env=env, input=input)
    if check and result.returncode != 0:
        if result.stdout:
            console.print(result.stdout)
        if result.stderr:
            console.print(f"[red]{result.stderr}[/red]")
        raise typer.Exit(result.returncode)
    return result


def load_env():
    """Carga variables desde .env si existe."""
    env_file = ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        console.print("[green]Cargado .env[/green]")


@app.command()
def init(
    overlay: str = typer.Option(
        "dev",
        "--overlay",
        "-o",
        help="Overlay a preparar",
    )
):
    """Validaciones básicas y presencia de kustomize/overlay."""
    load_env()
    if not shutil.which("kubectl") and not shutil.which("oc"):
        console.print("[red]kubectl u oc no encontrados[/red]")
        raise typer.Exit(1)
    if not shutil.which("kustomize"):
        console.print("[yellow]kustomize no encontrado[/yellow]")
        raise typer.Exit(1)
    path = ROOT / "deploy-gitops" / "overlays" / overlay
    if not path.exists():
        console.print(f"[red]Overlay no existe: {path}[/red]")
        raise typer.Exit(1)
    console.print(f"[green]Overlay listo:[/green] {path}")


@app.command()
def bootstrap(
    overlay: str = typer.Option("dev", "--overlay", "-o"),
    server_side: bool = typer.Option(
        True,
        "--server-side",
        "--no-server-side",
        help="Usar server-side apply",
        show_default=True,
    ),
):
    """Aplica recursos base (ns, rbac, pvc, cm, secrets) en el overlay indicado."""
    load_env()
    path = ROOT / "deploy-gitops" / "overlays" / overlay
    console.print(f"[cyan]Bootstrap {overlay}[/cyan]")
    cmd = [sys.executable, str(GITOPS), "apply", "--path", str(path), "--kustomize"]
    if server_side:
        cmd += ["--server-side"]
    run(cmd, check=False)


@app.command()
def sync(
    overlay: str = typer.Option("dev", "--overlay", "-o"),
    prune: bool = typer.Option(
        False,
        "--prune",
        "--no-prune",
        help="Eliminar recursos ausentes tras aplicar",
        show_default=True,
    ),
    server_side: bool = typer.Option(
        True,
        "--server-side",
        "--no-server-side",
        help="Usar server-side apply",
        show_default=True,
    ),
):
    """Sincroniza estado declarativo (plan → apply [+ prune])."""
    load_env()
    path = ROOT / "deploy-gitops" / "overlays" / overlay
    console.print(f"[cyan]Plan ({overlay})[/cyan]")
    run(
        [sys.executable, str(GITOPS), "plan", "--path", str(path), "--kustomize"],
        check=False,
    )
    console.print(f"[cyan]Apply ({overlay})[/cyan]")
    cmd = [sys.executable, str(GITOPS), "apply", "--path", str(path), "--kustomize"]
    if server_side:
        cmd += ["--server-side"]
    run(cmd, check=False)
    if prune:
        console.print(f"[cyan]Prune ({overlay})[/cyan]")
        prune_cmd = [
            sys.executable,
            str(GITOPS),
            "prune",
            "--path",
            str(path),
            "--kustomize",
        ]
        if server_side:
            prune_cmd.append("--server-side")
        prune_cmd += ["--selector", "gitops-lite=managed"]
        run(prune_cmd, check=False)
    console.print("[green]Sync OK[/green]")


@app.command()
def secrets(
    env: str = typer.Option("dev", "--env", "-e"),
    from_env: bool = typer.Option(
        True,
        "--from-env",
        "--no-from-env",
        help="Tomar secretos desde variables de entorno",
        show_default=True,
    ),
):  # noqa: ARG001
    """Configura secrets en GitHub desde variables .env o ambiente actual."""
    load_env()
    repo = os.getenv("REPO_SLUG")
    if not repo:
        console.print("[red]Define REPO_SLUG en .env[/red]")
        raise typer.Exit(1)
    gh = shutil.which("gh")
    if not gh:
        console.print("[red]Instala GitHub CLI (gh)[/red]")
        raise typer.Exit(1)

    if env == "dev":
        for key in ("K8S_SERVER_DEV", "K8S_TOKEN_DEV"):
            value = os.getenv(key)
            if not value:
                console.print(f"[yellow]Advertencia: {key} vacío[/yellow]")
            run(
                [gh, "secret", "set", key, "--repo", repo, "--body", value or ""],
                check=False,
            )
    console.print("[green]Secrets configurados[/green]")


@app.command()
def doctor():
    """Diagnóstico básico del entorno (CLI, cluster, overlays)."""
    load_env()

    def ok(cmd_name: str) -> bool:
        return shutil.which(cmd_name) is not None

    checks = {
        "python": ok("python3"),
        "kubectl_or_oc": ok("kubectl") or ok("oc"),
        "kustomize": ok("kustomize"),
        "git": ok("git"),
    }
    console.print(json.dumps(checks, indent=2))
    try:
        run(["kubectl", "version", "--short"], check=False)
    except Exception:  # pragma: no cover - fallback manual
        if shutil.which("oc"):
            run(["oc", "version"], check=False)
    console.print("[green]Doctor finalizado[/green]")


if __name__ == "__main__":
    app()

from __future__ import annotations

import json
import platform
import sys
from typing import Optional

import typer

from airi import __version__
from airi.config import ConfigLoadError, load_app_config
from airi.storage import StoragePaths

app = typer.Typer(help="AI Research Intelligence CLI")
config_app = typer.Typer(help="Validate and inspect configuration files.")
storage_app = typer.Typer(help="Inspect and initialize local storage directories.")
app.add_typer(config_app, name="config")
app.add_typer(storage_app, name="storage")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def version() -> None:
    """Print the package version."""
    typer.echo(__version__)


@app.command()
def doctor(
    config: Optional[str] = typer.Option(None, help="Optional path to a config file."),
) -> None:
    """Run a basic environment check."""
    typer.echo("Python: %s" % platform.python_version())
    typer.echo("Platform: %s" % platform.system())
    typer.echo("Path: %s" % sys.executable)
    if config:
        typer.echo("Config path: %s" % config)


@config_app.command("validate")
def validate_config() -> None:
    """Validate all default configuration files."""
    try:
        load_app_config()
    except ConfigLoadError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Configuration validation passed.")


@config_app.command("show")
def show_config() -> None:
    """Print a sanitized configuration summary."""
    try:
        config = load_app_config()
    except ConfigLoadError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(json.dumps(config.sanitized_summary(), ensure_ascii=False, indent=2))


@storage_app.command("doctor")
def storage_doctor() -> None:
    """Create public storage dirs and print storage paths."""
    paths = StoragePaths.default()
    paths.ensure_public_dirs()
    typer.echo("Storage directories:")
    typer.echo(f"  state:   {paths.state_dir} (public)")
    typer.echo(f"  reports: {paths.reports_dir} (public)")
    typer.echo(f"  sample:  {paths.sample_dir} (public)")
    typer.echo(f"  cache:   {paths.cache_dir} (private, gitignored)")
    typer.echo(f"  raw:     {paths.raw_dir} (private, gitignored)")


@storage_app.command("init")
def storage_init(
    private: bool = typer.Option(
        False,
        "--private",
        help="Also create private gitignored cache/raw directories.",
    ),
) -> None:
    """Initialize storage directories."""
    paths = StoragePaths.default()
    paths.ensure_public_dirs()
    typer.echo(
        "Created public storage directories: data/state, data/reports, data/sample"
    )
    if private:
        paths.ensure_private_dirs()
        typer.echo("Created private storage directories: data/cache, data/raw")

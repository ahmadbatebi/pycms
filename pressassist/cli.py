"""Command-line interface for ChelCheleh."""

import secrets
import sys
from pathlib import Path

import click

from .core.auth import AuthManager
from .core.config import AppConfig
from .core.storage import Storage


@click.group()
@click.version_option(prog_name="pressassist")
def main():
    """ChelCheleh - A secure, Python-based flat-file CMS."""
    pass


@main.command()
@click.option(
    "--dir",
    "-d",
    "base_dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Base directory for the site (default: current directory)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing database",
)
def init(base_dir: Path | None, force: bool):
    """Initialize a new ChelCheleh site.

    Creates the database, default content, and admin credentials.
    """
    if base_dir is None:
        base_dir = Path.cwd()

    config = AppConfig(base_dir=base_dir)
    config.ensure_directories()

    storage = Storage(config.db_path)

    if storage.exists and not force:
        click.echo(
            click.style("Error: ", fg="red")
            + f"Database already exists at {config.db_path}"
        )
        click.echo("Use --force to overwrite.")
        sys.exit(1)

    auth = AuthManager(bcrypt_rounds=config.bcrypt_rounds)

    # Generate secure credentials
    login_slug = auth.generate_login_slug()
    default_password = "Admin12345!"
    password_hash = auth.hash_password(default_password)

    # Initialize database
    storage.initialize(login_slug, password_hash)

    # Display results
    click.echo()
    click.echo(click.style("ChelCheleh initialized successfully!", fg="green", bold=True))
    click.echo()
    click.echo(click.style("=" * 60, fg="yellow"))
    click.echo(click.style("IMPORTANT: Save these credentials securely!", fg="yellow", bold=True))
    click.echo(click.style("=" * 60, fg="yellow"))
    click.echo()
    click.echo(f"  Login URL:  http://127.0.0.1:8000/{login_slug}")
    click.echo(f"  Username:   admin")
    click.echo(f"  Password:   {default_password}")
    click.echo()
    click.echo(click.style("Change your password after first login!", fg="red", bold=True))
    click.echo()
    click.echo("Next steps:")
    click.echo("  1. Run: pressassist run")
    click.echo("  2. Visit the login URL")
    click.echo("  3. Login with username 'admin' and password shown above")
    click.echo("  4. Change your password immediately")
    click.echo()


@main.command()
@click.option(
    "--host",
    "-h",
    default="127.0.0.1",
    help="Host to bind to (default: 127.0.0.1)",
)
@click.option(
    "--port",
    "-p",
    default=8000,
    type=int,
    help="Port to bind to (default: 8000)",
)
@click.option(
    "--reload",
    is_flag=True,
    help="Enable auto-reload for development",
)
@click.option(
    "--workers",
    "-w",
    default=1,
    type=int,
    help="Number of worker processes (default: 1)",
)
@click.option(
    "--dir",
    "-d",
    "base_dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Base directory for the site",
)
@click.option(
    "--ssl-keyfile",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to SSL key file for HTTPS",
)
@click.option(
    "--ssl-certfile",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to SSL certificate file for HTTPS",
)
def run(
    host: str,
    port: int,
    reload: bool,
    workers: int,
    base_dir: Path | None,
    ssl_keyfile: Path | None,
    ssl_certfile: Path | None,
):
    """Start the ChelCheleh server.

    For HTTPS (recommended), provide both --ssl-keyfile and --ssl-certfile.
    """
    import uvicorn

    if base_dir is None:
        base_dir = Path.cwd()

    config = AppConfig(base_dir=base_dir, host=host, port=port, workers=workers)

    if not config.db_path.exists():
        click.echo(
            click.style("Error: ", fg="red")
            + "Site not initialized. Run 'pressassist init' first."
        )
        sys.exit(1)

    # Validate SSL options
    if (ssl_keyfile is None) != (ssl_certfile is None):
        click.echo(
            click.style("Error: ", fg="red")
            + "Both --ssl-keyfile and --ssl-certfile must be provided together."
        )
        sys.exit(1)

    use_ssl = ssl_keyfile is not None and ssl_certfile is not None
    scheme = "https" if use_ssl else "http"

    click.echo(f"Starting ChelCheleh on {scheme}://{host}:{port}")
    if use_ssl:
        click.echo(click.style("HTTPS enabled", fg="green"))

    uvicorn_config = {
        "app": "pressassist.main:app",
        "host": host,
        "port": port,
        "reload": reload,
        "workers": workers if not reload else 1,
    }

    if use_ssl:
        uvicorn_config["ssl_keyfile"] = str(ssl_keyfile)
        uvicorn_config["ssl_certfile"] = str(ssl_certfile)

    uvicorn.run(**uvicorn_config)


@main.command()
@click.option(
    "--dir",
    "-d",
    "base_dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Base directory for the site",
)
def backup(base_dir: Path | None):
    """Create a backup of the site data."""
    import zipfile
    from datetime import datetime, timezone

    if base_dir is None:
        base_dir = Path.cwd()

    config = AppConfig(base_dir=base_dir)

    if not config.db_path.exists():
        click.echo(click.style("Error: ", fg="red") + "No site data found.")
        sys.exit(1)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_name = f"pressassist_backup_{timestamp}.zip"
    backup_path = config.backups_dir / backup_name

    config.backups_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add database
        zf.write(config.db_path, "db.json")

        # Add uploads
        if config.uploads_dir.exists():
            for file in config.uploads_dir.iterdir():
                if file.is_file():
                    zf.write(file, f"uploads/{file.name}")

    click.echo(
        click.style("Backup created: ", fg="green")
        + str(backup_path)
    )


@main.command()
@click.argument("backup_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--dir",
    "-d",
    "base_dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Base directory for the site",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing data",
)
def restore(backup_file: Path, base_dir: Path | None, force: bool):
    """Restore site data from a backup."""
    import zipfile

    if base_dir is None:
        base_dir = Path.cwd()

    config = AppConfig(base_dir=base_dir)

    if config.db_path.exists() and not force:
        click.echo(
            click.style("Error: ", fg="red")
            + "Existing data found. Use --force to overwrite."
        )
        sys.exit(1)

    # Validate zip file
    if not zipfile.is_zipfile(backup_file):
        click.echo(click.style("Error: ", fg="red") + "Invalid backup file.")
        sys.exit(1)

    with zipfile.ZipFile(backup_file, "r") as zf:
        # Check for required files
        names = zf.namelist()
        if "db.json" not in names:
            click.echo(
                click.style("Error: ", fg="red")
                + "Invalid backup: missing db.json"
            )
            sys.exit(1)

        # Security: Check for path traversal
        for name in names:
            if name.startswith("/") or ".." in name:
                click.echo(
                    click.style("Error: ", fg="red")
                    + f"Invalid path in backup: {name}"
                )
                sys.exit(1)

        # Validate database structure before restoring
        try:
            import json
            with zf.open("db.json") as db_file:
                db_data = json.load(db_file)

            # Validate required keys
            required_keys = {"config", "pages", "users"}
            missing_keys = required_keys - set(db_data.keys())
            if missing_keys:
                click.echo(
                    click.style("Error: ", fg="red")
                    + f"Invalid backup structure: missing {', '.join(missing_keys)}"
                )
                sys.exit(1)

            # Validate config has required fields
            config_data = db_data.get("config", {})
            if "login_slug" not in config_data:
                click.echo(
                    click.style("Error: ", fg="red")
                    + "Invalid backup: config missing login_slug"
                )
                sys.exit(1)

            # Validate admin user exists
            users_data = db_data.get("users", {})
            if "admin" not in users_data:
                click.echo(
                    click.style("Error: ", fg="red")
                    + "Invalid backup: missing admin user"
                )
                sys.exit(1)

            # Validate admin has password_hash
            admin_data = users_data.get("admin", {})
            if "password_hash" not in admin_data:
                click.echo(
                    click.style("Error: ", fg="red")
                    + "Invalid backup: admin user missing password_hash"
                )
                sys.exit(1)

            click.echo(click.style("Backup validation passed.", fg="green"))

        except json.JSONDecodeError as e:
            click.echo(
                click.style("Error: ", fg="red")
                + f"Invalid backup: db.json is not valid JSON ({e})"
            )
            sys.exit(1)

        config.ensure_directories()

        # Extract database
        zf.extract("db.json", config.data_dir)

        # Extract uploads
        for name in names:
            if name.startswith("uploads/") and not name.endswith("/"):
                zf.extract(name, config.data_dir)

    click.echo(click.style("Restore completed!", fg="green"))


@main.command("new-login-slug")
@click.option(
    "--dir",
    "-d",
    "base_dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Base directory for the site",
)
def new_login_slug(base_dir: Path | None):
    """Generate a new secret login URL."""
    if base_dir is None:
        base_dir = Path.cwd()

    config = AppConfig(base_dir=base_dir)
    storage = Storage(config.db_path)

    if not storage.exists:
        click.echo(click.style("Error: ", fg="red") + "Site not initialized.")
        sys.exit(1)

    auth = AuthManager()
    new_slug = auth.generate_login_slug()

    storage.load()
    storage.set("config.login_slug", new_slug)

    click.echo()
    click.echo(click.style("New login URL generated!", fg="green"))
    click.echo()
    click.echo(f"  New Login URL: http://127.0.0.1:8000/{new_slug}")
    click.echo()
    click.echo(click.style("Update your bookmarks!", fg="yellow"))
    click.echo()


@main.command("hash-password")
@click.option(
    "--password",
    "-p",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="Password to hash",
)
def hash_password(password: str):
    """Generate a bcrypt hash for a password."""
    auth = AuthManager()
    hash_str = auth.hash_password(password)

    click.echo()
    click.echo("Password hash (for manual database editing):")
    click.echo(hash_str)
    click.echo()


@main.command("check")
@click.option(
    "--dir",
    "-d",
    "base_dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Base directory for the site",
)
def check(base_dir: Path | None):
    """Check site configuration and dependencies."""
    if base_dir is None:
        base_dir = Path.cwd()

    config = AppConfig(base_dir=base_dir)

    click.echo("ChelCheleh Configuration Check")
    click.echo("=" * 40)
    click.echo()

    # Check directories
    click.echo("Directories:")
    for name, path in [
        ("Data", config.data_dir),
        ("Themes", config.themes_dir),
        ("Plugins", config.plugins_dir),
        ("Uploads", config.uploads_dir),
        ("Backups", config.backups_dir),
    ]:
        exists = path.exists()
        status = click.style("OK", fg="green") if exists else click.style("MISSING", fg="red")
        click.echo(f"  {name}: {path} [{status}]")

    click.echo()

    # Check database
    click.echo("Database:")
    if config.db_path.exists():
        click.echo(f"  {config.db_path} [" + click.style("OK", fg="green") + "]")

        storage = Storage(config.db_path)
        try:
            storage.load()
            click.echo("  Valid JSON: " + click.style("YES", fg="green"))
        except Exception as e:
            click.echo("  Valid JSON: " + click.style(f"NO ({e})", fg="red"))
    else:
        click.echo(
            f"  {config.db_path} ["
            + click.style("NOT INITIALIZED", fg="yellow")
            + "]"
        )

    click.echo()

    # Check themes
    click.echo("Themes:")
    if config.themes_dir.exists():
        themes = list(config.themes_dir.iterdir())
        if themes:
            for theme in themes:
                if theme.is_dir():
                    has_json = (theme / "theme.json").exists()
                    has_templates = (theme / "templates").exists()
                    if has_templates:
                        click.echo(f"  {theme.name} [" + click.style("OK", fg="green") + "]")
                    else:
                        click.echo(
                            f"  {theme.name} ["
                            + click.style("MISSING TEMPLATES", fg="yellow")
                            + "]"
                        )
        else:
            click.echo("  No themes found")
    else:
        click.echo("  Themes directory not found")

    click.echo()


if __name__ == "__main__":
    main()

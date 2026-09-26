"""Download the official Stockfish Windows build into engine/, where
explorer/engine.py expects to find it. The binary itself is gitignored
(engine/*.exe) rather than committed -- this command is how you (re)get it
on a fresh checkout."""

import io
import urllib.request
import zipfile

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

RELEASE_API_URL = "https://api.github.com/repos/official-stockfish/Stockfish/releases/latest"
TARGET_ASSET_NAME = "stockfish-windows-x86-64-universal.zip"


class Command(BaseCommand):
    help = "Download the latest official Stockfish Windows build into engine/."

    def handle(self, **options):
        import json

        engine_dir = settings.BASE_DIR / "engine"
        engine_dir.mkdir(exist_ok=True)
        target_path = engine_dir / "stockfish-windows-x86-64-avx2.exe"

        if target_path.exists():
            self.stdout.write(f"{target_path} already exists -- nothing to do.")
            return

        self.stdout.write("Looking up the latest Stockfish release...")
        with urllib.request.urlopen(RELEASE_API_URL) as resp:
            release = json.loads(resp.read())

        asset = next(
            (a for a in release.get("assets", []) if a["name"] == TARGET_ASSET_NAME), None
        )
        if asset is None:
            raise CommandError(f"Could not find {TARGET_ASSET_NAME} in the latest release assets.")

        self.stdout.write(f"Downloading {asset['name']} ({release['tag_name']})...")
        with urllib.request.urlopen(asset["browser_download_url"]) as resp:
            archive_bytes = resp.read()

        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zf:
            exe_names = [n for n in zf.namelist() if n.endswith(".exe")]
            if not exe_names:
                raise CommandError("No .exe found inside the downloaded archive.")
            with zf.open(exe_names[0]) as src, open(target_path, "wb") as dst:
                dst.write(src.read())

        self.stdout.write(self.style.SUCCESS(f"Installed Stockfish to {target_path}"))

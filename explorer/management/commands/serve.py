"""Run this project with waitress, a production-ready pure-Python WSGI
server, instead of `manage.py runserver` (which is single-threaded by
default and explicitly not meant for real concurrent multi-client use --
exactly the case once this is serving multiple LAN clients at once)."""

import socket

from django.core.management.base import BaseCommand
from django.core.wsgi import get_wsgi_application
from waitress import serve


class Command(BaseCommand):
    help = "Serve this project with waitress."

    def add_arguments(self, parser):
        parser.add_argument(
            "--host",
            default="127.0.0.1",
            help="Interface to bind. Use 0.0.0.0 to accept connections from other "
            "devices on the network, not just this machine.",
        )
        parser.add_argument("--port", type=int, default=8000)
        parser.add_argument(
            "--threads",
            type=int,
            default=8,
            help="Worker thread pool size, i.e. how many requests waitress can "
            "handle concurrently (default: 8).",
        )

    def handle(self, host, port, threads, **options):
        application = get_wsgi_application()

        self.stdout.write(self.style.SUCCESS(f"Serving on http://{host}:{port}/"))
        if host == "0.0.0.0":
            lan_ip = self._guess_lan_ip()
            if lan_ip:
                self.stdout.write(f"On this network, other devices can reach it at: http://{lan_ip}:{port}/")
        self.stdout.write("Press Ctrl+C to stop.")

        serve(application, host=host, port=port, threads=threads)

    @staticmethod
    def _guess_lan_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except OSError:
            return None
        finally:
            s.close()

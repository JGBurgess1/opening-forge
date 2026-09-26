"""Generate a small SYNTHETIC PGN file for exercising the ingestion
pipeline and the web GUI end-to-end.

These are NOT real grandmaster games. Each game starts from a real named
opening line (data/eco.tsv), continues with a bounded number of randomly
chosen legal moves, and ends with a randomly chosen result. Every game's
Event/White/Black headers make this clear.

Once you have a real games archive (e.g. an exported Lichess/TWIC/GM
database), ingest that instead with `manage.py ingest_pgn` and skip this
command entirely.
"""

import os
import random

import chess
from django.conf import settings
from django.core.management.base import BaseCommand

RESULTS = ["1-0", "0-1", "1/2-1/2"]
RESULT_WEIGHTS = [0.38, 0.32, 0.30]


class Command(BaseCommand):
    help = "Generate a synthetic sample PGN file for pipeline testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            default=os.path.join("data", "sample_games.pgn"),
            help="Output PGN path (default: data/sample_games.pgn).",
        )
        parser.add_argument(
            "--games-per-opening",
            type=int,
            default=6,
            help="How many synthetic games to generate per ECO opening line (default: 6).",
        )
        parser.add_argument(
            "--max-openings",
            type=int,
            default=120,
            help="Cap on how many ECO lines to use as book seeds (default: 120).",
        )
        parser.add_argument(
            "--extra-plies",
            type=int,
            default=10,
            help="Max number of extra random legal plies appended after the book line (default: 10).",
        )
        parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")

    def handle(self, out, games_per_opening, max_openings, extra_plies, seed, **options):
        rng = random.Random(seed)
        openings = self._load_openings()
        if not openings:
            self.stderr.write(self.style.ERROR("Could not load data/eco.tsv"))
            return

        rng.shuffle(openings)
        openings = openings[:max_openings]

        out_path = os.path.join(settings.BASE_DIR, out) if not os.path.isabs(out) else out
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        count = 0
        with open(out_path, "w", encoding="utf-8") as f:
            for opening in openings:
                for game_num in range(games_per_opening):
                    pgn = self._build_game(opening, extra_plies, rng, count)
                    if pgn is None:
                        continue
                    f.write(pgn)
                    f.write("\n\n")
                    count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Wrote {count} synthetic sample games to {out_path}")
        )

    def _load_openings(self):
        path = os.path.join(settings.BASE_DIR, "data", "eco.tsv")
        if not os.path.exists(path):
            return []

        openings = []
        with open(path, "r", encoding="utf-8") as f:
            next(f)
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) != 3:
                    continue
                eco, name, pgn = parts
                moves = [tok for tok in pgn.split() if not tok.endswith(".")]
                if moves:
                    openings.append({"eco": eco, "name": name, "moves": moves})
        return openings

    def _build_game(self, opening, extra_plies, rng, game_index):
        board = chess.Board()
        try:
            for san in opening["moves"]:
                board.push_san(san)
        except ValueError:
            return None

        n_extra = rng.randint(0, extra_plies)
        for _ in range(n_extra):
            legal = list(board.legal_moves)
            if not legal or board.is_game_over():
                break
            board.push(rng.choice(legal))

        result = board.result() if board.is_game_over() else rng.choices(RESULTS, RESULT_WEIGHTS)[0]

        white = f"Sample Player {game_index * 2 + 1}"
        black = f"Sample Player {game_index * 2 + 2}"

        headers = {
            "Event": "Synthetic Sample Dataset (NOT real games -- pipeline validation only)",
            "Site": "opening-forge sample data generator",
            "Date": "????.??.??",
            "Round": "-",
            "White": white,
            "Black": black,
            "Result": result,
            "ECO": opening["eco"],
            "Opening": opening["name"],
        }

        lines = [f'[{k} "{v}"]' for k, v in headers.items()]

        move_text = []
        replay = chess.Board()
        for i, move in enumerate(board.move_stack):
            san = replay.san(move)
            if i % 2 == 0:
                move_text.append(f"{i // 2 + 1}.{san}")
            else:
                move_text.append(san)
            replay.push(move)
        move_text.append(result)

        return "\n".join(lines) + "\n\n" + " ".join(move_text)

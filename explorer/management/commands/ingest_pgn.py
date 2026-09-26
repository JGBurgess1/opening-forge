"""Import a PGN file into the opening-move tree used by the web GUI.

For every game, every position reached along its mainline is folded into
a tree keyed by exact move sequence (PositionNode). Each node tracks how
many imported games passed through it and how those games were decided.
Nodes at or below settings.LOW_SAMPLE_THRESHOLD keep a link to the actual
Game rows so the UI can offer a "view the games" link instead of a
statistically meaningless win-rate breakdown.

This does an in-memory aggregation pass before writing to the database,
which is appropriate for the sample/validation datasets this project
ships with (hundreds to low thousands of games). Ingesting a real
multi-million-game archive would need a streaming/DB-side aggregation
strategy instead -- see README.md.
"""

import io

import chess
import chess.pgn
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from explorer.models import Game, PositionNode

RESULT_TO_BUCKET = {
    "1-0": "white",
    "0-1": "black",
    "1/2-1/2": "draw",
}


class _TrieNode:
    __slots__ = ("san", "fen", "total", "white", "draw", "black", "children", "game_idxs")

    def __init__(self, san, fen):
        self.san = san
        self.fen = fen
        self.total = 0
        self.white = 0
        self.draw = 0
        self.black = 0
        self.children = {}
        self.game_idxs = []

    def add_result(self, bucket, game_idx):
        self.total += 1
        if bucket == "white":
            self.white += 1
        elif bucket == "black":
            self.black += 1
        else:
            self.draw += 1
        self.game_idxs.append(game_idx)


class Command(BaseCommand):
    help = "Ingest a PGN file into the opening move tree."

    def add_arguments(self, parser):
        parser.add_argument("pgn_path", help="Path to a PGN file.")
        parser.add_argument(
            "--source-label",
            default="",
            help="Free-text label recorded on each imported game (e.g. dataset name).",
        )
        parser.add_argument(
            "--append",
            action="store_true",
            help="Keep existing games/tree and merge new games into them "
            "instead of clearing the database first.",
        )

    def handle(self, pgn_path, source_label, append, **options):
        parsed_games = list(self._parse_pgn(pgn_path, source_label))
        if not parsed_games:
            raise CommandError("No games with a decisive/drawn result were found to import.")

        self.stdout.write(f"Parsed {len(parsed_games)} games. Building move tree...")

        root = _TrieNode(san="", fen=chess.Board().fen())
        for idx, game in enumerate(parsed_games):
            bucket = RESULT_TO_BUCKET[game["result"]]
            node = root
            node.add_result(bucket, idx)
            board = chess.Board()
            for san in game["moves"]:
                board.push_san(san)
                child = node.children.get(san)
                if child is None:
                    child = _TrieNode(san=san, fen=board.fen())
                    node.children[san] = child
                child.add_result(bucket, idx)
                node = child

        self.stdout.write("Writing to database...")
        with transaction.atomic():
            if not append:
                PositionNode.objects.all().delete()
                Game.objects.all().delete()

            game_objs = Game.objects.bulk_create(
                Game(
                    white=g["white"],
                    black=g["black"],
                    white_elo=g["white_elo"],
                    black_elo=g["black_elo"],
                    result=g["result"],
                    event=g["event"],
                    site=g["site"],
                    date_played=g["date"],
                    source_label=source_label,
                    moves=g["moves"],
                    pgn_text=g["pgn_text"],
                )
                for g in parsed_games
            )

            threshold = settings.LOW_SAMPLE_THRESHOLD
            node_count = self._write_tree(root, parent=None, game_objs=game_objs, threshold=threshold)

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(parsed_games)} games into {node_count} position nodes."
            )
        )

    def _write_tree(self, trie_node, parent, game_objs, threshold):
        db_node = PositionNode.objects.create(
            parent=parent,
            san=trie_node.san,
            ply=(parent.ply + 1) if parent else 0,
            fen=trie_node.fen,
            total_games=trie_node.total,
            white_wins=trie_node.white,
            draws=trie_node.draw,
            black_wins=trie_node.black,
        )

        if trie_node.total <= threshold:
            db_node.sample_games.set([game_objs[i] for i in trie_node.game_idxs])

        total = 1
        for child in trie_node.children.values():
            total += self._write_tree(child, db_node, game_objs, threshold)
        return total

    def _parse_pgn(self, pgn_path, source_label):
        try:
            f = open(pgn_path, "r", encoding="utf-8", errors="replace")
        except OSError as exc:
            raise CommandError(f"Could not open {pgn_path}: {exc}")

        with f:
            while True:
                game = chess.pgn.read_game(f)
                if game is None:
                    break

                result = game.headers.get("Result", "*")
                if result not in RESULT_TO_BUCKET:
                    continue

                board = game.board()
                moves = []
                for move in game.mainline_moves():
                    moves.append(board.san(move))
                    board.push(move)

                if not moves:
                    continue

                exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
                pgn_text = game.accept(exporter)

                def to_int(value):
                    try:
                        return int(value)
                    except (TypeError, ValueError):
                        return None

                yield {
                    "white": game.headers.get("White", "?"),
                    "black": game.headers.get("Black", "?"),
                    "white_elo": to_int(game.headers.get("WhiteElo")),
                    "black_elo": to_int(game.headers.get("BlackElo")),
                    "result": result,
                    "event": game.headers.get("Event", ""),
                    "site": game.headers.get("Site", ""),
                    "date": game.headers.get("Date", ""),
                    "moves": moves,
                    "pgn_text": pgn_text,
                }

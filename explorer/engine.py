"""Thin wrapper around a persistent Stockfish process for on-demand
position analysis (as opposed to the precomputed evaluations in
data/opening_evals.json, which only cover known ECO lines).

Spawning a UCI engine process costs real startup latency, so one
process is kept alive for the lifetime of the server and reused across
requests. A lock serializes access to it: UCI engines aren't safe for
concurrent use from multiple threads, which matters once more than one
client is hitting the analysis endpoint at the same time (as happens
once this is served to several LAN clients through waitress's thread
pool). Callers just wait their turn; there's no request queue limit
because analyse() is time-bounded (see api_analyze's movetime cap).
"""

import atexit
import threading

import chess
import chess.engine
from django.conf import settings

STOCKFISH_PATH = settings.BASE_DIR / "engine" / "stockfish-windows-x86-64-avx2.exe"

_engine = None
_engine_lock = threading.Lock()


def is_available():
    return STOCKFISH_PATH.exists()


def _get_engine():
    global _engine
    if _engine is None:
        _engine = chess.engine.SimpleEngine.popen_uci(str(STOCKFISH_PATH))
        atexit.register(_shutdown)
    return _engine


def _shutdown():
    global _engine
    if _engine is not None:
        try:
            _engine.quit()
        except Exception:
            pass
        _engine = None


def analyze_fen(fen, movetime=1.0, depth=None):
    board = chess.Board(fen)

    if board.is_game_over():
        return {"game_over": True, "evaluation": None, "mate_in": None, "best_move": None, "pv": [], "depth": None}

    limit = chess.engine.Limit(depth=depth) if depth else chess.engine.Limit(time=movetime)

    with _engine_lock:
        info = _get_engine().analyse(board, limit)

    score = info["score"].white()
    if score.is_mate():
        evaluation = None
        mate_in = score.mate()
    else:
        evaluation = round(score.score() / 100.0, 2)
        mate_in = None

    pv = info.get("pv", [])
    pv_san = []
    replay = board.copy()
    for move in pv[:8]:
        pv_san.append(replay.san(move))
        replay.push(move)

    return {
        "game_over": False,
        "evaluation": evaluation,
        "mate_in": mate_in,
        "best_move": pv_san[0] if pv_san else None,
        "pv": pv_san,
        "depth": info.get("depth"),
    }

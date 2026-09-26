import chess
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from . import eco
from .models import Game, PositionNode


def index(request):
    return render(request, "explorer/index.html", {
        "low_sample_threshold": settings.LOW_SAMPLE_THRESHOLD,
    })


def _path_to(node):
    """List of SAN moves from the root down to (and including) node."""
    moves = []
    cur = node
    while cur.parent_id is not None:
        moves.append(cur.san)
        cur = cur.parent
    moves.reverse()
    return moves


def _serialize_node(node):
    path = _path_to(node)
    opening = eco.lookup(path)

    children = list(
        node.children.all().order_by("-total_games", "san")
    )

    return {
        "id": node.id,
        "san": node.san,
        "fen": node.fen,
        "ply": node.ply,
        "path": path,
        "opening": {"eco": opening[0], "name": opening[1]} if opening else None,
        "total_games": node.total_games,
        "win_rates": node.win_rates(),
        "is_low_sample": node.total_games <= settings.LOW_SAMPLE_THRESHOLD and node.total_games > 0,
        "low_sample_threshold": settings.LOW_SAMPLE_THRESHOLD,
        "children": [
            {
                "id": child.id,
                "san": child.san,
                "total_games": child.total_games,
                "win_rates": child.win_rates(),
            }
            for child in children
        ],
    }


@require_GET
def api_root(request):
    node = PositionNode.objects.filter(parent__isnull=True).first()
    if node is None:
        return JsonResponse(
            {"error": "No games have been ingested yet. Run 'manage.py ingest_pgn' first."},
            status=404,
        )
    return JsonResponse(_serialize_node(node))


@require_GET
def api_node_detail(request, node_id):
    node = get_object_or_404(PositionNode, pk=node_id)
    return JsonResponse(_serialize_node(node))


@require_GET
def api_move(request, node_id):
    san = request.GET.get("san", "").strip()
    if not san:
        return JsonResponse({"error": "Missing 'san' query parameter."}, status=400)

    node = get_object_or_404(PositionNode, pk=node_id)

    child = node.children.filter(san=san).first()
    if child is not None:
        return JsonResponse(_serialize_node(child))

    # Off-book move: not present in the imported games. Validate legality
    # against the position's FEN and return a zero-stats, unsaved node so
    # the board can still advance.
    board = chess.Board(node.fen)
    try:
        board.push_san(san)
    except ValueError:
        return JsonResponse({"error": f"Illegal move: {san}"}, status=400)

    path = _path_to(node) + [san]
    opening = eco.lookup(path)

    return JsonResponse({
        "id": None,
        "san": san,
        "fen": board.fen(),
        "ply": node.ply + 1,
        "path": path,
        "opening": {"eco": opening[0], "name": opening[1]} if opening else None,
        "total_games": 0,
        "win_rates": {"white": 0.0, "draw": 0.0, "black": 0.0},
        "is_low_sample": False,
        "low_sample_threshold": settings.LOW_SAMPLE_THRESHOLD,
        "children": [],
        "no_data": True,
    })


@require_GET
def api_low_sample_games(request, node_id):
    node = get_object_or_404(PositionNode, pk=node_id)
    if node.total_games == 0 or node.total_games > settings.LOW_SAMPLE_THRESHOLD:
        return JsonResponse(
            {"error": "This position is not at or below the low-sample threshold."},
            status=400,
        )

    games = node.sample_games.all()
    return JsonResponse({
        "games": [
            {
                "id": g.id,
                "white": g.white,
                "black": g.black,
                "white_elo": g.white_elo,
                "black_elo": g.black_elo,
                "result": g.result,
                "event": g.event,
                "site": g.site,
                "date_played": g.date_played,
                "source_label": g.source_label,
                "move_count": len(g.moves),
            }
            for g in games
        ]
    })


@require_GET
def api_game_detail(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    return JsonResponse({
        "id": game.id,
        "white": game.white,
        "black": game.black,
        "result": game.result,
        "event": game.event,
        "site": game.site,
        "date_played": game.date_played,
        "moves": game.moves,
        "pgn_text": game.pgn_text,
    })

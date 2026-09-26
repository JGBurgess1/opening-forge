from django.db import models


class Game(models.Model):
    """A single imported game, kept around so low-sample lines can link
    back to the actual games behind the statistics."""

    white = models.CharField(max_length=200)
    black = models.CharField(max_length=200)
    white_elo = models.IntegerField(null=True, blank=True)
    black_elo = models.IntegerField(null=True, blank=True)
    RESULT_CHOICES = [
        ("1-0", "White wins"),
        ("0-1", "Black wins"),
        ("1/2-1/2", "Draw"),
    ]
    result = models.CharField(max_length=10, choices=RESULT_CHOICES)
    event = models.CharField(max_length=300, blank=True)
    site = models.CharField(max_length=300, blank=True)
    date_played = models.CharField(max_length=20, blank=True)
    source_label = models.CharField(max_length=200, blank=True)
    moves = models.JSONField(help_text="Full move list in SAN.")
    pgn_text = models.TextField()

    def __str__(self):
        return f"{self.white} vs {self.black} ({self.result})"


class PositionNode(models.Model):
    """One node in the opening move tree: the position reached after a
    specific sequence of moves from the starting position. Children are
    the candidate next moves seen in the imported games."""

    parent = models.ForeignKey(
        "self", null=True, blank=True, related_name="children", on_delete=models.CASCADE
    )
    san = models.CharField(
        max_length=16, blank=True, help_text="Move (SAN) that led from the parent to this node."
    )
    ply = models.PositiveIntegerField(default=0)
    fen = models.CharField(max_length=100)

    total_games = models.PositiveIntegerField(default=0)
    white_wins = models.PositiveIntegerField(default=0)
    draws = models.PositiveIntegerField(default=0)
    black_wins = models.PositiveIntegerField(default=0)

    sample_games = models.ManyToManyField(
        Game,
        blank=True,
        related_name="position_nodes",
        help_text="Only populated for positions at or below the low-sample threshold.",
    )

    class Meta:
        unique_together = [("parent", "san")]
        indexes = [models.Index(fields=["parent", "san"])]

    def __str__(self):
        return self.san or "(start)"

    def win_rates(self):
        if not self.total_games:
            return {"white": 0.0, "draw": 0.0, "black": 0.0}
        return {
            "white": round(100 * self.white_wins / self.total_games, 1),
            "draw": round(100 * self.draws / self.total_games, 1),
            "black": round(100 * self.black_wins / self.total_games, 1),
        }

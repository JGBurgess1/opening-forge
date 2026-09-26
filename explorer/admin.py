from django.contrib import admin

from .models import Game, PositionNode


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("white", "black", "result", "event", "date_played", "source_label")
    search_fields = ("white", "black", "event")


@admin.register(PositionNode)
class PositionNodeAdmin(admin.ModelAdmin):
    list_display = ("id", "san", "ply", "total_games", "white_wins", "draws", "black_wins")
    list_filter = ("ply",)

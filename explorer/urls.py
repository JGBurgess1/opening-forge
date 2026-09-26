from django.urls import path

from . import views

app_name = "explorer"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/root/", views.api_root, name="api_root"),
    path("api/node/<int:node_id>/", views.api_node_detail, name="api_node_detail"),
    path("api/node/<int:node_id>/move/", views.api_move, name="api_move"),
    path("api/node/<int:node_id>/games/", views.api_low_sample_games, name="api_low_sample_games"),
    path("api/game/<int:game_id>/", views.api_game_detail, name="api_game_detail"),
]

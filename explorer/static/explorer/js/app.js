(function () {
  "use strict";

  var game = new Chess();
  var board = null;
  var pathStack = []; // stack of node JSON objects, root first

  var $movesBody = document.querySelector("#moves-table tbody");
  var $openingName = document.getElementById("opening-name");
  var $positionSummary = document.getElementById("position-summary");
  var $lowSampleBanner = document.getElementById("low-sample-banner");
  var $lowSampleCount = document.getElementById("low-sample-count");
  var $noDataMsg = document.getElementById("no-data-msg");
  var $btnBack = document.getElementById("btn-back");
  var $btnReset = document.getElementById("btn-reset");
  var $btnViewGames = document.getElementById("btn-view-games");
  var $moveHistory = document.getElementById("move-history");
  var $modal = document.getElementById("games-modal");
  var $gamesList = document.getElementById("games-list");
  var $btnCloseModal = document.getElementById("btn-close-modal");

  function currentNode() {
    return pathStack[pathStack.length - 1];
  }

  function fmtPct(v) {
    return v.toFixed(1) + "%";
  }

  function renderMoveHistory() {
    var sanList = pathStack.slice(1).map(function (n) { return n.san; });
    var parts = [];
    for (var i = 0; i < sanList.length; i++) {
      if (i % 2 === 0) parts.push((i / 2 + 1) + "." + sanList[i]);
      else parts.push(sanList[i]);
    }
    $moveHistory.textContent = parts.join(" ") || "(starting position)";
  }

  function renderNode(node) {
    if (node.opening) {
      $openingName.textContent = node.opening.name + " (" + node.opening.eco + ")";
    } else {
      $openingName.textContent = pathStack.length > 1 ? "Unclassified line" : "";
    }

    var wr = node.win_rates;
    if (node.total_games > 0) {
      $positionSummary.textContent =
        node.total_games + " game(s) in database -- White " + fmtPct(wr.white) +
        " / Draw " + fmtPct(wr.draw) + " / Black " + fmtPct(wr.black);
    } else {
      $positionSummary.textContent = "";
    }

    $movesBody.innerHTML = "";
    node.children.forEach(function (child) {
      var tr = document.createElement("tr");
      tr.className = "move-row";
      tr.innerHTML =
        "<td class=\"move-cell\">" + child.san + "</td>" +
        "<td>" + child.total_games + "</td>" +
        "<td>" + fmtPct(child.win_rates.white) + "</td>" +
        "<td>" + fmtPct(child.win_rates.draw) + "</td>" +
        "<td>" + fmtPct(child.win_rates.black) + "</td>";
      tr.addEventListener("click", function () { playSan(child.san); });
      $movesBody.appendChild(tr);
    });

    $noDataMsg.hidden = !(node.no_data && node.children.length === 0);

    if (node.is_low_sample) {
      $lowSampleBanner.hidden = false;
      $lowSampleCount.textContent = node.total_games;
    } else {
      $lowSampleBanner.hidden = true;
    }

    $btnBack.disabled = pathStack.length <= 1;
    renderMoveHistory();
  }

  function pushNode(node) {
    pathStack.push(node);
    renderNode(node);
  }

  function fetchJSON(url) {
    return fetch(url).then(function (res) {
      if (!res.ok) {
        return res.json().then(function (body) {
          throw new Error(body.error || ("HTTP " + res.status));
        });
      }
      return res.json();
    });
  }

  function playSan(san) {
    var move = game.move(san);
    if (!move) return; // shouldn't happen for moves sourced from the DB/board

    board.position(game.fen());

    var current = currentNode();

    if (current.id === null) {
      // Already off-book: every descendant is off-book too, no need to
      // ask the server (there is nothing in the database to look up).
      pushNode({
        id: null,
        san: san,
        fen: game.fen(),
        total_games: 0,
        win_rates: { white: 0, draw: 0, black: 0 },
        is_low_sample: false,
        children: [],
        opening: null,
        no_data: true,
      });
      return;
    }

    fetchJSON("/api/node/" + current.id + "/move/?san=" + encodeURIComponent(san))
      .then(pushNode)
      .catch(function (err) {
        console.error(err);
        game.undo();
        board.position(game.fen());
      });
  }

  function onDrop(source, target) {
    var move = game.move({ from: source, to: target, promotion: "q" });
    if (move === null) return "snapback";

    board.position(game.fen());
    var san = move.san;
    game.undo(); // playSan() re-applies it after confirming with the server
    board.position(game.fen());
    playSan(san);
  }

  function resetToRoot() {
    game.reset();
    board.start();
    pathStack = [pathStack[0]];
    renderNode(pathStack[0]);
  }

  function goBack() {
    if (pathStack.length <= 1) return;
    pathStack.pop();
    var target = currentNode();
    game.load(target.fen);
    board.position(target.fen);
    renderNode(target);
  }

  function openGamesModal() {
    var node = currentNode();
    if (node.id === null) return;

    fetchJSON("/api/node/" + node.id + "/games/").then(function (data) {
      $gamesList.innerHTML = "";
      data.games.forEach(function (g) {
        var div = document.createElement("div");
        div.className = "game-entry";
        div.innerHTML =
          "<strong>" + g.white + "</strong> vs <strong>" + g.black + "</strong>" +
          " (" + g.result + ")<br>" +
          "<span class=\"game-meta\">" + (g.event || "") + " " + (g.date_played || "") + "</span>" +
          (g.source_label ? "<br><span class=\"game-meta\">" + g.source_label + "</span>" : "") +
          " <a href=\"/api/game/" + g.id + "/\" target=\"_blank\">view full PGN</a>";
        $gamesList.appendChild(div);
      });
      $modal.hidden = false;
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    board = Chessboard("board", {
      position: "start",
      draggable: true,
      onDrop: onDrop,
      pieceTheme: window.EXPLORER_CONFIG.pieceTheme,
    });

    $btnReset.addEventListener("click", resetToRoot);
    $btnBack.addEventListener("click", goBack);
    $btnViewGames.addEventListener("click", openGamesModal);
    $btnCloseModal.addEventListener("click", function () { $modal.hidden = true; });

    fetchJSON(window.EXPLORER_CONFIG.rootUrl)
      .then(function (root) {
        pathStack = [root];
        renderNode(root);
      })
      .catch(function (err) {
        $positionSummary.textContent = "Error: " + err.message;
      });
  });
})();

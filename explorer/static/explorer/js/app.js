(function () {
  "use strict";

  var game = new Chess();
  var board = null;
  var pathStack = []; // stack of node JSON objects, root first
  var mode = "explorer"; // "explorer" | "viewer"

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

  var $explorerView = document.getElementById("explorer-view");
  var $viewerView = document.getElementById("game-viewer-view");
  var $btnExitViewer = document.getElementById("btn-exit-viewer");
  var $viewerHeader = document.getElementById("viewer-game-header");
  var $viewerStepLabel = document.getElementById("viewer-step-label");
  var $viewerMoveList = document.getElementById("viewer-move-list");
  var $btnViewerFirst = document.getElementById("btn-viewer-first");
  var $btnViewerPrev = document.getElementById("btn-viewer-prev");
  var $btnViewerNext = document.getElementById("btn-viewer-next");
  var $btnViewerLast = document.getElementById("btn-viewer-last");

  var $btnAnalyze = document.getElementById("btn-analyze");
  var $engineResult = document.getElementById("engine-result");

  function currentNode() {
    return pathStack[pathStack.length - 1];
  }

  function fmtPct(v) {
    return v.toFixed(1) + "%";
  }

  function buildBarHTML(wr) {
    return (
      '<div class="wdb-bar" title="White ' + fmtPct(wr.white) + ' / Draw ' +
      fmtPct(wr.draw) + ' / Black ' + fmtPct(wr.black) + '">' +
      '<span class="wdb-white" style="width:' + wr.white + '%"></span>' +
      '<span class="wdb-draw" style="width:' + wr.draw + '%"></span>' +
      '<span class="wdb-black" style="width:' + wr.black + '%"></span>' +
      "</div>"
    );
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
      $positionSummary.innerHTML =
        node.total_games + " game(s) in database " + buildBarHTML(wr);
    } else {
      $positionSummary.innerHTML = "";
    }

    $movesBody.innerHTML = "";
    node.children.forEach(function (child) {
      var tr = document.createElement("tr");
      tr.className = "move-row";
      tr.innerHTML =
        "<td class=\"move-cell\">" + child.san + "</td>" +
        "<td>" + child.total_games + "</td>" +
        "<td class=\"bar-cell\">" + buildBarHTML(child.win_rates) + "</td>" +
        "<td class=\"pct-cell\">" + fmtPct(child.win_rates.white) + " / " +
          fmtPct(child.win_rates.draw) + " / " + fmtPct(child.win_rates.black) + "</td>";
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
    clearEngineResult();
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

  // Assumes `game` (chess.js) already has the move applied -- looks the
  // resulting position up against the database and updates the panels.
  function confirmMove(san) {
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

  // Used when a move is chosen by clicking a row in the moves table --
  // chess.js hasn't applied it yet.
  function playSan(san) {
    var move = game.move(san);
    if (!move) return; // shouldn't happen for moves sourced from the DB
    board.position(game.fen());
    confirmMove(san);
  }

  // Dragging a piece on the board. Per chessboard.js's own guidance, the
  // board position must NOT be touched from inside onDrop -- do it in
  // onSnapEnd once the built-in drag animation has finished, or the
  // board's internal drag state and our position updates race each other.
  var pendingSan = null;

  function onDrop(source, target) {
    if (mode !== "explorer") return "snapback";
    var move = game.move({ from: source, to: target, promotion: "q" });
    if (move === null) return "snapback";
    pendingSan = move.san;
  }

  function onSnapEnd() {
    board.position(game.fen());
    if (pendingSan) {
      var san = pendingSan;
      pendingSan = null;
      confirmMove(san);
    }
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
          "<br><button class=\"play-through-btn\">Play through this game</button>";
        div.querySelector(".play-through-btn").addEventListener("click", function () {
          $modal.hidden = true;
          enterGameViewer(g.id);
        });
        $gamesList.appendChild(div);
      });
      $modal.hidden = false;
    });
  }

  // --- Game viewer: step through one specific historical game on the
  // main board, independent of the opening-tree exploration state. ---

  var viewerMoves = [];
  var viewerIndex = 0; // number of moves played so far (0 = start position)
  var viewerCurrentFen = null;

  function enterGameViewer(gameId) {
    fetchJSON("/api/game/" + gameId + "/").then(function (g) {
      mode = "viewer";
      viewerMoves = g.moves;
      viewerIndex = 0; // start from the beginning of the game

      $viewerHeader.innerHTML =
        "<strong>" + g.white + "</strong> vs <strong>" + g.black + "</strong> (" + g.result + ")" +
        "<br><span class=\"game-meta\">" + (g.event || "") + " " + (g.date_played || "") + "</span>";

      $viewerMoveList.innerHTML = "";
      for (var i = 0; i < viewerMoves.length; i++) {
        var span = document.createElement("span");
        span.className = "viewer-move-token";
        span.dataset.index = i + 1;
        var prefix = i % 2 === 0 ? (i / 2 + 1) + "." : "";
        span.textContent = prefix + viewerMoves[i] + " ";
        span.addEventListener("click", function () {
          viewerIndex = parseInt(this.dataset.index, 10);
          renderViewerStep();
        });
        $viewerMoveList.appendChild(span);
      }

      $explorerView.hidden = true;
      $viewerView.hidden = false;
      $btnReset.disabled = true;
      $btnBack.disabled = true;
      renderViewerStep();
    });
  }

  function renderViewerStep() {
    var replay = new Chess();
    for (var i = 0; i < viewerIndex; i++) replay.move(viewerMoves[i]);
    viewerCurrentFen = replay.fen();
    board.position(viewerCurrentFen);

    $viewerStepLabel.textContent = viewerIndex + " / " + viewerMoves.length;

    var tokens = $viewerMoveList.querySelectorAll(".viewer-move-token");
    tokens.forEach(function (t) {
      t.classList.toggle("active", parseInt(t.dataset.index, 10) === viewerIndex);
    });

    $btnViewerFirst.disabled = $btnViewerPrev.disabled = viewerIndex === 0;
    $btnViewerLast.disabled = $btnViewerNext.disabled = viewerIndex === viewerMoves.length;
    clearEngineResult();
  }

  function viewerStepPrev() {
    if (mode !== "viewer") return;
    viewerIndex = Math.max(0, viewerIndex - 1);
    renderViewerStep();
  }

  function viewerStepNext() {
    if (mode !== "viewer") return;
    viewerIndex = Math.min(viewerMoves.length, viewerIndex + 1);
    renderViewerStep();
  }

  function exitViewer() {
    mode = "explorer";
    $viewerView.hidden = true;
    $explorerView.hidden = false;
    $btnReset.disabled = false;
    var node = currentNode();
    game.load(node.fen);
    board.position(node.fen);
    renderNode(node); // recompute $btnBack.disabled from pathStack.length
  }

  // --- Live Stockfish analysis of whatever position is currently on the
  // board, in either explorer or viewer mode. ---

  function activeFen() {
    return mode === "viewer" ? viewerCurrentFen : game.fen();
  }

  function clearEngineResult() {
    $engineResult.innerHTML = "";
  }

  function runAnalysis() {
    var fen = activeFen();
    if (!fen) return;

    $btnAnalyze.disabled = true;
    $engineResult.textContent = "Analyzing...";

    fetchJSON(window.EXPLORER_CONFIG.analyzeUrl + "?fen=" + encodeURIComponent(fen))
      .then(function (data) {
        if (data.game_over) {
          $engineResult.textContent = "Game over in this position.";
          return;
        }
        var evalText = (data.mate_in !== null && data.mate_in !== undefined)
          ? "Mate in " + Math.abs(data.mate_in)
          : (data.evaluation > 0 ? "+" : "") + data.evaluation;
        $engineResult.innerHTML =
          "<strong>Eval:</strong> " + evalText +
          " &nbsp; <strong>Best move:</strong> " + (data.best_move || "-") +
          "<br><strong>Line:</strong> " + data.pv.join(" ");
      })
      .catch(function (err) {
        $engineResult.textContent = "Error: " + err.message;
      })
      .then(function () { $btnAnalyze.disabled = false; });
  }

  document.addEventListener("DOMContentLoaded", function () {
    board = Chessboard("board", {
      position: "start",
      draggable: true,
      onDrop: onDrop,
      onSnapEnd: onSnapEnd,
      pieceTheme: window.EXPLORER_CONFIG.pieceTheme,
    });

    $btnReset.addEventListener("click", resetToRoot);
    $btnBack.addEventListener("click", goBack);
    $btnViewGames.addEventListener("click", openGamesModal);
    $btnAnalyze.addEventListener("click", runAnalysis);
    $btnCloseModal.addEventListener("click", function () { $modal.hidden = true; });

    $btnExitViewer.addEventListener("click", exitViewer);
    $btnViewerFirst.addEventListener("click", function () { viewerIndex = 0; renderViewerStep(); });
    $btnViewerPrev.addEventListener("click", viewerStepPrev);
    $btnViewerNext.addEventListener("click", viewerStepNext);
    $btnViewerLast.addEventListener("click", function () { viewerIndex = viewerMoves.length; renderViewerStep(); });

    document.addEventListener("keydown", function (e) {
      if (mode !== "viewer") return;
      if (e.key === "ArrowRight") {
        e.preventDefault();
        viewerStepNext();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        viewerStepPrev();
      }
    });

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

# ♟️ Opening Forge

### Open-Source Chess Opening Intelligence Platform

Most chess opening tools answer:

> **"What opening is this?"**

Opening Forge aims to answer:

> **Why do I play this opening?**  
> **Which openings fit my style?**  
> **How has my repertoire evolved?**  
> **Which grandmasters think like me?**  
> **What should I learn next?**

Opening Forge is an open-source platform for analyzing, understanding, and discovering chess openings.

Built on top of the complete Lichess ECO database, the project combines opening theory, engine analysis, player profiling, and chess analytics into a single platform for chess players.

---

## 📸 Opening Recognition + Engine Analysis

![Opening Demo](assets/opening-demo.png)

Recognize openings from user-entered moves and retrieve engine evaluations, best moves, and principal variations from a database of 3700+ openings.

---

## 🚧 Current Status

### Implemented

- Recognition of 3700+ openings and variations
- Complete Lichess ECO database integration
- SAN move validation using `python-chess`
- Deepest opening detection
- Fast indexed opening lookup
- Engine evaluation database generation
- Principal variation extraction
- Best move recommendations
- Position database generation
- FEN indexing framework
- Command-line opening explorer

### Currently Working On

- Position intelligence system
- Position-to-opening recognition
- Transposition detection
- Opening analytics
- Interactive platform development

---

## ✨ Features

### Current Features

- Opening recognition from move sequences
- ECO classification
- Deep opening matching
- SAN move validation
- Engine evaluations
- Best move recommendations
- Principal variation analysis
- Position database generation
- FEN indexing
- Fast indexed search

### Planned Features

- Position explorer
- Opening analytics
- Player DNA system
- Personalized opening recommendations
- Automated repertoire generation
- Opening cards
- Chess personality profiles
- Interactive dashboard
- Opening Wrapped reports

For the complete roadmap, see **ROADMAP.md**.

---

## 🛠 Technical Screenshots

### Engine Evaluation Database

![Evaluation Database](assets/eval-database.png)

Engine-generated evaluation dataset containing evaluations, best moves, and principal variations for thousands of opening positions.

---

### Position Intelligence Dataset

![Position Database](assets/fen-database.png)

FEN-indexed opening position database that enables future position recognition and transposition detection.

---

### Codebase Overview

![Codebase Overview](assets/project-workspace.png)

Opening Forge workspace showing project organization, datasets, engine integration, scripts, and supporting documentation.

---

### Repository Structure

![Repository Structure](assets/repo-structure.png)

Project organization showing data pipelines, engine integration, scripts, source code, and documentation.

---

## 🚀 Example

### Input

```text
e4
e5
Nf3
Nc6
Bc4
```

### Output

```text
Opening Name:
Italian Game (C50)

Evaluation:
0.00

Best Move:
Bc5

Principal Variation:
Bc5 c3 Nf6 d4 exd4
```

---

## 🖥️ Web GUI (Opening Explorer)

A Django web application lives alongside the CLI tool: an interactive
chessboard where the move panel next to the board updates after every move
with the win-rate breakdown (White / Draw / Black) for every reply seen in
the imported games, drawn from a database of real grandmaster games.
When a line has been played in **3 or fewer** imported games, the
breakdown is replaced with a link to view those exact games (players,
event, result, full PGN) instead of a statistically meaningless
percentage split.

### Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # on Windows
# source .venv/bin/activate   # on macOS/Linux

pip install -r requirements.txt

python manage.py migrate
```

### Get some games into the database

The repository does not ship a multi-million-game archive. To try the
GUI immediately, generate a small **synthetic** sample dataset (clearly
labeled as such in every game's PGN headers) built from real ECO opening
lines with randomized legal continuations and results:

```bash
python manage.py generate_sample_pgn
python manage.py ingest_pgn data/sample_games.pgn --source-label "Synthetic sample"
```

To use **real games**, ingest any standard PGN file the same way:

```bash
python manage.py ingest_pgn path/to/real_grandmaster_games.pgn --source-label "My GM archive"
```

#### Ingesting a full public archive (e.g. a Lichess database dump)

Public archives like the [Lichess open database](https://database.lichess.org/)
are monthly dumps of every rated game played by every player, not just
strong ones -- a single month can be millions of games, most of them
club-level. Use `--min-elo` to pull out just the games played by strong
players; games that don't meet it are rejected from a cheap header-only
scan and never get their moves parsed, so this is fast even against a
multi-gigabyte file:

```bash
python manage.py ingest_pgn path/to/lichess_db_standard_rated_YYYY-MM.pgn \
    --min-elo 2200 \
    --source-label "Lichess standard rated games, YYYY-MM, both players >=2200"
```

`--min-elo N` keeps only games where **both** players' Elo is at or
above `N`. Note this is not the same as "grandmaster games" -- these
archives don't carry player titles, only ratings, so a high Elo cutoff
is a proxy for strong play, not a guarantee of a titled opponent on
either side.

The matched games are still aggregated into the move tree fully
in-memory before being written to the database in one transaction,
which is fine for the kind of subset `--min-elo` produces out of a
monthly dump (thousands to tens of thousands of games). Ingesting an
entire *unfiltered* multi-million-game archive would need a further
streaming/DB-side aggregation rewrite of the tree-writing step -- the
model layer (`PositionNode`, `Game`) doesn't need to change for that,
only the ingestion strategy.

### Run it (just for yourself)

```bash
python manage.py runserver
```

Then open <http://127.0.0.1:8000/> in a browser.

### Live engine analysis (optional)

Besides the win-rate database, the board has an "Analyze position
(Stockfish)" button that asks the server to run a real engine search on
whatever position is currently on screen (including off-book positions
the imported games never reached), instead of only looking up the
precomputed evaluations in `data/opening_evals.json`.

This needs a Stockfish binary on the server machine:

```bash
python manage.py setup_engine
```

This downloads the latest official Stockfish Windows build into
`engine/` (gitignored -- each machine gets its own copy rather than
this being committed). If the binary isn't present, the Analyze button
still works but the server returns a "no chess engine installed" error
instead of a crash.

One Stockfish process is kept running for the lifetime of the server
and shared across all requests/clients (spawning a fresh engine process
per request would add ~1s of startup latency to every analysis). A lock
serializes access to it, and each analysis request is capped at 5
seconds, so one slow client can't block everyone else indefinitely --
but note this does mean analysis requests from different clients queue
up rather than running in parallel.

### Hosting it for other devices on your network

The GUI is a normal web app, so any browser -- including on another
computer or a phone -- can use it once the server is listening on your
network instead of just `127.0.0.1`. Two things to change from the
"just for yourself" setup:

**1. Use a real server, not the Django dev server.** `manage.py
runserver` is single-threaded by default and explicitly not meant for
concurrent multi-client use, which is exactly the situation once
several devices are hitting it at once. This project includes a
`serve` command that runs it under [waitress](https://docs.pylonsproject.org/projects/waitress/)
instead, a production-ready pure-Python WSGI server:

```bash
python manage.py serve --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` binds every network interface, not just localhost.
The command prints the LAN URL to share with other devices, e.g.
`http://192.168.1.42:8000/` -- use `ipconfig` (Windows) / `ifconfig` /
`ip addr` if you need to find that address yourself. Every client just
opens that URL in a browser; there's no separate client install.

**2. Allow the port through Windows Firewall.** Windows blocks inbound
connections to a new listening port by default. Run this once, from an
**elevated** (Run as Administrator) PowerShell prompt:

```powershell
New-NetFirewallRule -DisplayName "Opening Forge" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -Profile Private
```

(`-Profile Private` scopes this to trusted networks like your home
Wi-Fi, not public ones.)

This setup is meant for a trusted local network (home Wi-Fi, a LAN
party, a classroom), not the public internet -- `DEBUG = True` in
`config/settings.py` is left on for easier troubleshooting, which means
anyone who *can* reach the server sees full Django error pages
(stack traces, file paths) if something breaks. Turn it off
(`DEBUG = False`) and put a real value in `SECRET_KEY` before exposing
this any more broadly than that.

---

## 📚 Documentation

- 📍 **ROADMAP.md** — Project vision and development roadmap
- 🏗️ **ARCHITECTURE.md** — System design and technical architecture
- 🤝 **CONTRIBUTING.md** — Contributor guide and development workflow

---

## 🎯 Why Opening Forge?

Most opening tools focus on identification.

Most training tools focus on memorization.

Opening Forge focuses on understanding.

The goal is to help players answer questions such as:

- Which openings fit my natural style?
- Which positions am I most comfortable playing?
- How has my repertoire changed over time?
- Which players have similar opening preferences?
- What should I learn next?
- Which openings should I add to my repertoire?
- Which positions consistently give me trouble?

Rather than being another opening encyclopedia, Opening Forge aims to become a platform for discovering the relationships between openings, positions, engine evaluations, and player behavior.

---

## 🤝 Contributing

Opening Forge welcomes contributions of all sizes.

Contributions are especially welcome in:

- Python development
- Chess analytics
- Data engineering
- Machine learning
- Frontend development
- UI/UX design
- Documentation

If you're interested in chess, analytics, or open-source development, check **CONTRIBUTING.md** to get started.

You can also look for issues labeled:

- `good first issue`
- `help wanted`

---

## 🏗️ Long-Term Vision

Opening Forge is not intended to be another opening explorer.

The long-term goal is to build a complete Chess Opening Intelligence Platform that connects:

- Openings
- Positions
- Engine evaluations
- Player styles
- Repertoires
- Historical trends
- Recommendation systems

into a single interconnected system.

Ultimately, Opening Forge aims to help players understand not only **what they play**, but **why they play it**.

---

## 📄 License

An open-source license will be added before the first major release.

---

## ⭐ Support

If you find Opening Forge interesting, consider starring the repository.

Feature ideas, bug reports, discussions, and pull requests are always appreciated.

---

> **Transforming chess openings from a collection of moves into a system of insights, relationships, and player understanding.**

# ImplCraft Web Platform

Professional design management platform for IC backend flows. Provides a SQLite database for design data, Git version control for design files, and a web frontend for monitoring and control.

## Architecture

```
┌─────────────────────────────────────────────┐
│              Web Frontend                    │
│  Dashboard │ Metrics │ Scripts │ Git        │
│  (HTML/CSS/JS served by FastAPI)            │
└──────────────────┬──────────────────────────┘
                   │ REST API + WebSocket
┌──────────────────┴──────────────────────────┐
│              FastAPI Backend                 │
│  /api/designs  /api/stages  /api/metrics    │
│  /api/scripts  /api/git     /api/dashboard  │
└─────┬──────────┬──────────────┬─────────────┘
      │          │              │
┌─────┴───┐ ┌───┴─────┐ ┌─────┴──────┐
│ SQLite   │ │  Git    │ │  File System│
│ (DB)     │ │ (VCS)   │ │ (Artifacts) │
└─────────┘ └─────────┘ └────────────┘
```

## Quick Start

```bash
# Install dependencies
pip install -r web/backend/requirements.txt

# Start the server
python run_web.py

# Or with custom settings
python run_web.py --port 9000 --host 0.0.0.0 --reload
```

Then open:
- **Dashboard**: http://localhost:8000/
- **API Docs**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `IMPLCRAFT_DB` | `data/implcraft.db` | SQLite database path |
| `IMPLCRAFT_PORT` | `8000` | Server port |
| `IMPLCRAFT_HOST` | `127.0.0.1` | Bind address |
| `IMPLCRAFT_GIT_REPO` | `.` | Git repository path |

## API Endpoints

### Dashboard
- `GET /api/dashboard/summary` — High-level metrics
- `GET /api/dashboard/activity` — Recent activity feed
- `GET /api/dashboard/designs-overview` — All designs with status

### Designs
- `GET /api/designs` — List all designs
- `POST /api/designs` — Create a new design
- `GET /api/designs/{id}` — Get design details
- `PUT /api/designs/{id}` — Update design
- `DELETE /api/designs/{id}` — Delete design
- `GET /api/designs/{id}/config` — Get YAML config content

### Stages
- `GET /api/stages/{design_id}` — List stages for a design
- `POST /api/stages/run` — Run a flow stage
- `GET /api/stages/detail/{stage_id}` — Stage details
- `GET /api/stages/{design_id}/log/{stage_name}` — Stage log
- `GET /api/stages/{design_id}/flow-status` — Overall flow status

### Metrics
- `GET /api/metrics/{design_id}` — Metrics history
- `POST /api/metrics/{design_id}` — Record metrics snapshot
- `GET /api/metrics/{design_id}/trends` — Trend data for charts

### Scripts
- `GET /api/scripts/{design_id}` — List scripts
- `POST /api/scripts/generate` — Generate script (preview)
- `GET /api/scripts/preview/{id}` — Script preview
- `POST /api/scripts/execute` — Execute confirmed script
- `POST /api/scripts/cancel/{id}` — Cancel running script
- `GET /api/scripts/log/{id}` — Execution log

### Git
- `GET /api/git/status` — Working tree status
- `POST /api/git/commit` — Commit changes
- `GET /api/git/log` — Commit history
- `GET /api/git/diff` — Diff between commits
- `GET /api/git/branches` — List branches
- `GET /api/git/file` — File content at commit
- `GET /api/git/file-history` — File commit history

### WebSocket
- `WS /ws/progress` — Real-time progress updates

## Database Schema

### designs
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment ID |
| name | VARCHAR(256) | Design name (unique) |
| top_module | VARCHAR(256) | Top-level module name |
| config_path | VARCHAR(1024) | YAML config file path |
| pdk_name | VARCHAR(128) | PDK technology name |
| clock_period_ns | FLOAT | Target clock period |
| status | VARCHAR(32) | Design status |

### stages
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment ID |
| design_id | INTEGER FK | Parent design |
| stage_name | VARCHAR(64) | Stage name |
| tool | VARCHAR(64) | EDA tool name |
| status | VARCHAR(32) | Stage status |
| timing_wns | FLOAT | Worst negative Slack |
| timing_tns | FLOAT | Total Negative Slack |
| area_utilization | FLOAT | Area utilization ratio |
| route_drc_errors | INTEGER | DRC error count |

### metrics
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment ID |
| design_id | INTEGER FK | Parent design |
| iteration | INTEGER | Iteration number |
| wns / tns | FLOAT | Timing metrics |
| utilization | FLOAT | Area utilization |
| total_power_mw | FLOAT | Total power |
| drc_errors | INTEGER | DRC errors |

### scripts
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment ID |
| design_id | INTEGER FK | Parent design |
| content | TEXT | Script content |
| preview_content | TEXT | Annotated preview |
| status | VARCHAR(32) | generated/running/completed |
| exit_code | INTEGER | Process exit code |

### git_commits
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment ID |
| commit_hash | VARCHAR(40) | Full SHA hash |
| author | VARCHAR(256) | Commit author |
| message | TEXT | Commit message |
| files_changed | INTEGER | Number of files changed |

## Script Preview & Execution Workflow

1. **Generate**: Script content is generated and stored with status `generated`
2. **Preview**: Frontend displays annotated preview with line numbers and comments
3. **Confirm**: User reviews and clicks "Confirm & Execute"
4. **Execute**: Script runs in subprocess, output captured to log
5. **Update**: Script record updated with exit code and log tail

This ensures human-in-the-loop control over EDA tool execution.

## Project Structure

```
ImplCraft/
├── web/
│   ├── backend/
│   │   ├── main.py              # FastAPI application
│   │   ├── db/
│   │   │   ├── engine.py        # SQLite + SQLAlchemy setup
│   │   │   ├── models.py        # ORM models
│   │   │   └── schemas.py       # Pydantic schemas
│   │   ├── git/
│   │   │   └── manager.py       # Git operations wrapper
│   │   ├── api/
│   │   │   ├── dashboard.py     # Dashboard endpoints
│   │   │   ├── designs.py       # Design CRUD
│   │   │   ├── stages.py        # Stage management
│   │   │   ├── metrics.py       # QoR metrics
│   │   │   ├── scripts.py       # Script preview/execute
│   │   │   └── git.py           # Git API
│   │   └── services/
│   │       └── script_executor.py  # Script execution engine
│   └── frontend/
│       ├── index.html           # Main SPA page
│       ├── css/style.css        # Dark theme stylesheet
│       └── js/app.js            # Frontend application
├── run_web.py                   # Server launcher
└── WEB_PLATFORM.md              # This file
```

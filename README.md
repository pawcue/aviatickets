# Aviatickets – step 1: app + database

Seat booking service (no payments). Python (FastAPI) + PostgreSQL + plain HTML/CSS/JS.

```
aviatickets/
├── backend/
│   ├── main.py            # API endpoints (all business logic)
│   ├── db.py              # connection to PostgreSQL
│   ├── schema.sql         # tables + demo flights
│   └── requirements.txt   # Python libraries
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js
```

## 1. Install system packages (Ubuntu)

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib python3 python3-venv python3-pip
```

Check that PostgreSQL is running:

```bash
sudo systemctl status postgresql
# If it is not active:  sudo systemctl enable --now postgresql
```

## 2. Create the database and a user

PostgreSQL has a system user `postgres`. We use it once to create our own user and database:

```bash
sudo -u postgres psql -c "CREATE USER aviatickets WITH PASSWORD 'aviatickets';"
sudo -u postgres psql -c "CREATE DATABASE aviatickets OWNER aviatickets;"
```

Test the connection (password: `aviatickets`):

```bash
psql "postgresql://aviatickets:aviatickets@localhost:5432/aviatickets" -c "SELECT 1;"
```

The connection string format is `postgresql://USER:PASSWORD@HOST:PORT/DATABASE`.

## 3. Python environment and libraries

```bash
cd aviatickets/backend
python3 -m venv .venv            # isolated environment for this project
source .venv/bin/activate        # your prompt now starts with (.venv)
pip install --upgrade pip
pip install -r requirements.txt
```

| Library | What for |
|---|---|
| `fastapi` | web framework: describes endpoints |
| `uvicorn` | server that runs FastAPI |
| `psycopg[binary]` | driver to talk to PostgreSQL |

## 4. Run

```bash
# still in aviatickets/backend with (.venv) active
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- App: http://localhost:8000
- Auto-generated API docs (try endpoints right there): http://localhost:8000/docs
- Health check: http://localhost:8000/health

On start the app runs `schema.sql`: creates the tables and 4 demo flights (only once).

To use a different database, set the variable before starting:

```bash
export DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/DBNAME"
```

## 5. Look inside the database

```bash
psql "postgresql://aviatickets:aviatickets@localhost:5432/aviatickets"
```
```sql
\dt                          -- list tables
SELECT * FROM flights;
SELECT * FROM bookings;
\q
```

## How booking works (read `backend/main.py`)

1. Browser asks `GET /api/flights` → list of flights with free seats.
2. User opens a flight → `GET /api/flights/{id}/seats` → list of taken seats, the map is drawn.
3. User sends the form → `POST /api/bookings`. The backend validates the seat and inserts a row.
4. **No double booking:** `UNIQUE (flight_id, seat)` in `schema.sql`. If two users click the same seat at the same moment, PostgreSQL rejects the second `INSERT`, and the API returns `409`.
5. `GET /api/bookings/{code}` finds a booking, `DELETE /api/bookings/{code}` cancels it.

## Troubleshooting

| Problem | Fix |
|---|---|
| `connection refused` | PostgreSQL is not running: `sudo systemctl start postgresql` |
| `password authentication failed` | Re-check user/password from step 2, or the `DATABASE_URL` variable |
| `pip install` fails to build something | `pip install --upgrade pip`, then retry (new Python versions need new wheels) |
| `ModuleNotFoundError` | Virtual env is not active: `source .venv/bin/activate` |
| Port 8000 is busy | Use `--port 8001` |

## Next steps for your DevOps roadmap

1. **Dockerfile** for the backend + **docker-compose.yml** with `db` (postgres image, volume) and `backend`. In `DATABASE_URL` the host becomes the service name `db`.
2. **Nginx**: serve `frontend/` as static files and proxy `/api` to several backend replicas (load balancing). Then remove the frontend mount at the bottom of `main.py`.
3. **Prometheus metrics**: add `/metrics` to the backend (e.g. `prometheus-fastapi-instrumentator`), custom counter for bookings.
4. **Grafana**: dashboards for requests/s, errors, latency, bookings count, plus Postgres exporter.

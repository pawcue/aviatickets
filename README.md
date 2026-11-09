## Tools used in this project

### Application

| Tool | What it does |
|---|---|
| **Python** | Programming language of the backend. |
| **FastAPI** | Web framework. Describes the API endpoints (flights, seats, bookings) and validates incoming data. |
| **Uvicorn** | Server that runs the FastAPI app and handles HTTP requests. |
| **Pydantic** | Checks request data (name, email, seat) before it reaches the database. It comes with FastAPI. |
| **psycopg 3** | Python driver for PostgreSQL. The app sends plain SQL queries through it. |
| **PostgreSQL** | Database. Stores flights and bookings. A `UNIQUE (flight_id, seat)` rule makes double booking of one seat impossible. |
| **HTML / CSS / JavaScript** | Frontend without frameworks: flight list, seat map, booking form. It talks to the backend with `fetch()`. |

### Infrastructure

| Tool | What it does |
|---|---|
| **Docker** | Packs the backend into an image, so it runs the same on any machine. |
| **Docker Compose** | Starts the whole project with one command: database, 3 backend replicas, Nginx, Prometheus and Grafana. |
| **Nginx** | Reverse proxy and load balancer. Receives all user requests and spreads them between the backend replicas (round-robin). It also hides the `/metrics` endpoint from the outside. |

### Monitoring

| Tool | What it does |
|---|---|
| **prometheus-fastapi-instrumentator** | Adds a `/metrics` endpoint to the backend: number of requests, status codes, response time. |
| **prometheus-client** | Python library for our own metrics: created bookings, cancelled bookings, seat conflicts. |
| **Prometheus** | Collects metrics from every backend replica every 5 seconds and stores them as time series. |
| **Grafana** | Draws the metrics as dashboards. The data source and the dashboard are loaded automatically (provisioning). |

### Development

| Tool | What it does |
|---|---|
| **Git / GitHub** | Version control. Work is done in a `feature` branch and merged into `main` with a merge commit, so the history stays visible. |
| **venv + pip** | Isolated Python environment and package installer for local runs without Docker. |
| **psql** | Command-line client to look inside the database and run SQL queries. |

### How the parts work together

```
Browser -> Nginx -> Backend (x3, FastAPI) -> PostgreSQL
                       ^
        Prometheus -----+  (collects metrics from each replica)
             ^
          Grafana  (shows dashboards)
```
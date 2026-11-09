"""Aviatickets backend: a small REST API for booking plane seats (no payment)."""
import re
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from psycopg.errors import UniqueViolation
from prometheus_client import Counter
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field

from db import get_connection, init_db

SEAT_LETTERS = "ABCDEF"  # 6 seats in every row


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # runs once when the server starts
    yield


app = FastAPI(title="Aviatickets", lifespan=lifespan)

# ---------- Metrics (Prometheus) ----------
# Automatic HTTP metrics (requests, status codes, latency) and the GET /metrics endpoint
Instrumentator(excluded_handlers=["/metrics"]).instrument(app).expose(app, include_in_schema=False)

# Our own business metrics (counters only grow; Prometheus computes rates from them)
BOOKINGS_CREATED = Counter("aviatickets_bookings_created_total", "Seats booked")
BOOKINGS_CANCELLED = Counter("aviatickets_bookings_cancelled_total", "Bookings cancelled")
BOOKING_CONFLICTS = Counter("aviatickets_booking_conflicts_total", "Attempts to book an already taken seat")


# ---------- Helpers ----------

def make_booking_code() -> str:
    """Random code like 'K7X2QP'. No 0/O/1/I so it is easy to read aloud."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(6))


def is_valid_seat(seat: str, seat_rows: int) -> bool:
    """'12C' is valid if row 12 exists on this plane and C is one of A-F."""
    match = re.fullmatch(r"(\d{1,2})([A-F])", seat)
    return bool(match) and 1 <= int(match.group(1)) <= seat_rows


# ---------- Request model ----------

class BookingRequest(BaseModel):
    flight_id: int
    seat: str
    passenger_name: str = Field(min_length=2, max_length=100)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=200)


# ---------- API ----------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/flights")
def list_flights():
    """All upcoming flights with the number of free seats."""
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT f.id, f.flight_number, f.origin, f.destination, f.departs_at,
                   f.seat_rows,
                   f.seat_rows * 6 - COUNT(b.id) AS free_seats
            FROM flights f
            LEFT JOIN bookings b ON b.flight_id = f.id
            WHERE f.departs_at > now()
            GROUP BY f.id
            ORDER BY f.departs_at
            """
        ).fetchall()


@app.get("/api/flights/{flight_id}/seats")
def flight_seats(flight_id: int):
    """Flight info + the list of already booked seats, e.g. ['1A', '12C']."""
    with get_connection() as conn:
        flight = conn.execute(
            "SELECT * FROM flights WHERE id = %s", (flight_id,)
        ).fetchone()
        if flight is None:
            raise HTTPException(404, "Flight not found")

        rows = conn.execute(
            "SELECT seat FROM bookings WHERE flight_id = %s", (flight_id,)
        ).fetchall()

    flight["taken_seats"] = [row["seat"] for row in rows]
    flight["seat_letters"] = SEAT_LETTERS
    return flight


@app.post("/api/bookings", status_code=201)
def create_booking(data: BookingRequest):
    """Book one seat. Returns the booking code."""
    code = make_booking_code()
    try:
        with get_connection() as conn:
            flight = conn.execute(
                "SELECT seat_rows FROM flights WHERE id = %s", (data.flight_id,)
            ).fetchone()
            if flight is None:
                raise HTTPException(404, "Flight not found")
            if not is_valid_seat(data.seat, flight["seat_rows"]):
                raise HTTPException(400, "This seat does not exist on the plane")

            conn.execute(
                """
                INSERT INTO bookings (booking_code, flight_id, seat, passenger_name, email)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (code, data.flight_id, data.seat, data.passenger_name.strip(), data.email),
            )
    except UniqueViolation:
        # UNIQUE (flight_id, seat) in schema.sql fired: someone was faster.
        BOOKING_CONFLICTS.inc()
        raise HTTPException(409, f"Seat {data.seat} was just taken. Please pick another one.")

    BOOKINGS_CREATED.inc()
    return {"booking_code": code, "seat": data.seat}


@app.get("/api/bookings/{code}")
def get_booking(code: str):
    with get_connection() as conn:
        booking = conn.execute(
            """
            SELECT b.booking_code, b.seat, b.passenger_name, b.email, b.created_at,
                   f.flight_number, f.origin, f.destination, f.departs_at
            FROM bookings b
            JOIN flights f ON f.id = b.flight_id
            WHERE b.booking_code = %s
            """,
            (code.upper(),),
        ).fetchone()
    if booking is None:
        raise HTTPException(404, "Booking not found. Check the code and try again.")
    return booking


@app.delete("/api/bookings/{code}")
def cancel_booking(code: str):
    with get_connection() as conn:
        deleted = conn.execute(
            "DELETE FROM bookings WHERE booking_code = %s RETURNING id", (code.upper(),)
        ).fetchone()
    if deleted is None:
        raise HTTPException(404, "Booking not found. Check the code and try again.")
    BOOKINGS_CANCELLED.inc()
    return {"status": "cancelled"}


# ---------- Frontend ----------
# Must be LAST, otherwise it would swallow the /api routes.
# Later Nginx will serve these files instead.
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

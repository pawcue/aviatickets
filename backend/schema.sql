-- Runs on every start of the app, so every statement must be safe to repeat.

CREATE TABLE IF NOT EXISTS flights (
    id            SERIAL PRIMARY KEY,
    flight_number TEXT        NOT NULL,
    origin        TEXT        NOT NULL,
    destination   TEXT        NOT NULL,
    departs_at    TIMESTAMPTZ NOT NULL,
    seat_rows     INTEGER     NOT NULL CHECK (seat_rows > 0)  -- 6 seats per row (A-F)
);

CREATE TABLE IF NOT EXISTS bookings (
    id             SERIAL PRIMARY KEY,
    booking_code   TEXT        NOT NULL UNIQUE,
    flight_id      INTEGER     NOT NULL REFERENCES flights(id) ON DELETE CASCADE,
    seat           TEXT        NOT NULL,                      -- e.g. "12C"
    passenger_name TEXT        NOT NULL,
    email          TEXT        NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- The database itself guarantees that one seat cannot be booked twice,
    -- even if two people click "Book" at the same moment.
    UNIQUE (flight_id, seat)
);

-- Demo flights (only inserted when the table is empty)
INSERT INTO flights (flight_number, origin, destination, departs_at, seat_rows)
SELECT * FROM (VALUES
    ('AV101', 'Frankfurt (FRA)', 'Lisbon (LIS)',    now() + interval '3 days',  20),
    ('AV202', 'Frankfurt (FRA)', 'Rome (FCO)',      now() + interval '5 days',  15),
    ('AV303', 'Berlin (BER)',    'Barcelona (BCN)', now() + interval '7 days',  18),
    ('AV404', 'Munich (MUC)',    'Athens (ATH)',    now() + interval '10 days', 12)
) AS demo(flight_number, origin, destination, departs_at, seat_rows)
WHERE NOT EXISTS (SELECT 1 FROM flights);

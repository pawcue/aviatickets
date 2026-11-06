// Frontend logic: talks to the backend through fetch() and draws the page.

const state = { flight: null, seat: null };

// Shortcut: $("name") == document.getElementById("name")
const $ = (id) => document.getElementById(id);

// ---------- Helpers ----------

// One place for all requests. Throws an Error with a readable message on failure.
async function api(path, options = {}) {
  const response = await fetch("/api" + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = typeof data.detail === "string" ? data.detail : "Please check the entered data.";
    throw new Error(message);
  }
  return data;
}

function formatDate(isoString) {
  return new Date(isoString).toLocaleString("en-GB", {
    weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

// Show one "screen" and hide the others
function show(sectionId) {
  for (const id of ["flights-section", "booking-section", "done-section"]) {
    $(id).hidden = id !== sectionId;
  }
}

// ---------- Step 1: flights list ----------

async function loadFlights() {
  const flights = await api("/flights");
  const list = $("flights");
  list.innerHTML = "";

  for (const flight of flights) {
    const card = document.createElement("article");
    card.className = "flight";

    const number = document.createElement("div");
    number.className = "flight-number";
    number.textContent = flight.flight_number;

    const info = document.createElement("div");
    const route = document.createElement("div");
    route.className = "flight-route";
    route.textContent = `${flight.origin} → ${flight.destination}`;
    const meta = document.createElement("div");
    meta.className = "flight-meta";
    meta.textContent = `${formatDate(flight.departs_at)} · ${flight.free_seats} seats left`;
    info.append(route, meta);

    const button = document.createElement("button");
    button.className = "btn";
    button.textContent = "Choose seat";
    button.disabled = flight.free_seats === 0;
    button.addEventListener("click", () => openFlight(flight.id));

    card.append(number, info, button);
    list.append(card);
  }
}

// ---------- Step 2: seat map ----------

async function openFlight(flightId) {
  state.flight = await api(`/flights/${flightId}/seats`);
  state.seat = null;

  $("booking-title").textContent =
    `${state.flight.flight_number}: ${state.flight.origin} → ${state.flight.destination}`;
  $("form-error").textContent = "";
  drawPlane();
  updateChosenSeat();
  show("booking-section");
}

function drawPlane() {
  const { seat_rows, seat_letters, taken_seats } = state.flight;
  const plane = $("plane");
  plane.innerHTML = "";

  for (let row = 1; row <= seat_rows; row++) {
    const rowElement = document.createElement("div");
    rowElement.className = "seat-row";

    const number = document.createElement("span");
    number.className = "row-number";
    number.textContent = row;
    rowElement.append(number);

    for (const letter of seat_letters) {
      if (letter === "D") {
        const aisle = document.createElement("span");
        aisle.className = "aisle";
        rowElement.append(aisle);
      }

      const seatName = `${row}${letter}`;
      const seat = document.createElement("button");
      seat.type = "button";
      seat.className = "seat";
      seat.textContent = letter;
      seat.setAttribute("aria-label", `Seat ${seatName}`);
      seat.disabled = taken_seats.includes(seatName);
      if (seatName === state.seat) seat.classList.add("selected");
      seat.addEventListener("click", () => selectSeat(seatName));
      rowElement.append(seat);
    }
    plane.append(rowElement);
  }
}

function selectSeat(seatName) {
  state.seat = seatName;
  drawPlane();
  updateChosenSeat();
}

function updateChosenSeat() {
  $("chosen-seat").textContent = state.seat ? `Seat ${state.seat}` : "Select a seat on the plane";
  $("book-btn").disabled = !state.seat;
}

// ---------- Step 3: send the booking ----------

$("booking-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("form-error").textContent = "";

  try {
    const result = await api("/bookings", {
      method: "POST",
      body: JSON.stringify({
        flight_id: state.flight.id,
        seat: state.seat,
        passenger_name: $("name").value,
        email: $("email").value,
      }),
    });

    $("done-code").textContent = result.booking_code;
    $("done-text").textContent =
      `Seat ${result.seat} on ${state.flight.flight_number} is yours. Save the code to find or cancel your booking.`;
    show("done-section");
    $("booking-form").reset();
  } catch (error) {
    $("form-error").textContent = error.message;
    // The seat may have been taken by someone else: refresh the map
    if (state.flight) {
      state.flight = await api(`/flights/${state.flight.id}/seats`);
      if (state.flight.taken_seats.includes(state.seat)) state.seat = null;
      drawPlane();
      updateChosenSeat();
    }
  }
});

$("back-btn").addEventListener("click", backToFlights);
$("again-btn").addEventListener("click", backToFlights);

async function backToFlights() {
  show("flights-section");
  await loadFlights();
}

// ---------- Find / cancel booking ----------

let foundCode = null;

$("lookup-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("lookup-error").textContent = "";
  $("lookup-result").hidden = true;

  try {
    const code = $("lookup-code").value.trim().toUpperCase();
    const booking = await api(`/bookings/${code}`);
    foundCode = booking.booking_code;

    const rows = [
      ["Passenger", booking.passenger_name],
      ["Flight", booking.flight_number],
      ["Route", `${booking.origin} → ${booking.destination}`],
      ["Departure", formatDate(booking.departs_at)],
      ["Seat", booking.seat],
    ];
    const details = $("lookup-details");
    details.innerHTML = "";
    for (const [label, value] of rows) {
      const dt = document.createElement("dt");
      dt.textContent = label;
      const dd = document.createElement("dd");
      dd.textContent = value; // textContent (not innerHTML) keeps user input safe
      details.append(dt, dd);
    }
    $("lookup-result").hidden = false;
  } catch (error) {
    $("lookup-error").textContent = error.message;
  }
});

$("cancel-btn").addEventListener("click", async () => {
  if (!confirm("Cancel this booking?")) return;
  try {
    await api(`/bookings/${foundCode}`, { method: "DELETE" });
    $("lookup-result").hidden = true;
    $("lookup-error").textContent = "Booking cancelled.";
    await loadFlights();
  } catch (error) {
    $("lookup-error").textContent = error.message;
  }
});

// ---------- Start ----------
loadFlights().catch((error) => {
  $("flights").textContent = "Could not load flights: " + error.message;
});

/* Week-grid interaction: click a free cell to book, click a booking to edit. */
(function () {
  "use strict";

  const modal = document.getElementById("booking-modal");
  if (!modal) return;

  const form = document.getElementById("booking-form");
  const el = (id) => document.getElementById(id);
  const errBox = el("f-error");

  // Time options: starts 09:00–17:00, ends 09:30–18:00 (18:00 shown as "late").
  const times = [];
  for (let h = 9; h <= 18; h++) for (const m of [0, 30]) {
    if (h === 18 && m === 30) break;
    times.push(`${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`);
  }
  const label = (t) => (t === "18:00" ? "18:00 (late)" : t);
  el("f-start").innerHTML = times.slice(0, -2)
    .map((t) => `<option value="${t}">${label(t)}</option>`).join("");
  el("f-end").innerHTML = times.slice(1)
    .map((t) => `<option value="${t}">${label(t)}</option>`).join("");

  function showError(msg) { errBox.textContent = msg; errBox.hidden = !msg; }

  function openModal({ title, bookingId, roomId, roomName, date, start, end,
                       activity = "", teacher = "", notes = "", meta = "" }) {
    el("modal-title").textContent = title;
    el("f-booking-id").value = bookingId || "";
    el("f-room-id").value = roomId;
    el("f-room-name").textContent = roomName;
    el("f-date").value = date;
    el("f-start").value = start;
    el("f-end").value = end;
    el("f-activity").value = activity;
    el("f-teacher").value = teacher;
    el("f-notes").value = notes;
    el("f-meta").textContent = meta;
    el("f-repeat").checked = false;
    document.getElementById("repeat-opts").hidden = true;
    // Repeats only make sense when creating, not editing one occurrence.
    document.getElementById("repeat-box").hidden = Boolean(bookingId);
    showError("");
    modal.showModal();
  }

  function addMinutes(t, mins) {
    const [h, m] = t.split(":").map(Number);
    const total = h * 60 + m + mins;
    return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
  }

  document.querySelectorAll("table.daygrid").forEach((table) => {
    table.addEventListener("click", async (ev) => {
      const cell = ev.target.closest("td");
      if (!cell) return;
      const row = cell.closest("tr");

      if (cell.classList.contains("free")) {
        const start = cell.dataset.slot;
        openModal({
          title: "New booking",
          roomId: row.dataset.room,
          roomName: row.dataset.roomName,
          date: table.dataset.date,
          start: start,
          end: start === "17:00" ? "18:00" : addMinutes(start, 60),
        });
      } else if (cell.classList.contains("booked")) {
        const resp = await fetch(`/api/bookings/${cell.dataset.booking}`);
        if (!resp.ok) return;
        const b = await resp.json();
        openModal({
          title: "Edit booking",
          bookingId: b.id,
          roomId: b.room_id,
          roomName: b.room,
          date: b.date,
          start: b.start,
          end: b.end,
          activity: b.activity,
          teacher: b.teacher,
          notes: b.notes,
          meta: `Booked by ${b.booked_by || "unknown"}` +
                (b.series_id ? " · part of a weekly repeat (edits apply to this date only)" : ""),
        });
      }
    });
  });

  el("f-repeat").addEventListener("change", (ev) => {
    document.getElementById("repeat-opts").hidden = !ev.target.checked;
  });
  el("f-cancel").addEventListener("click", () => modal.close());

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const bookingId = el("f-booking-id").value;
    const payload = {
      room_id: el("f-room-id").value,
      date: el("f-date").value,
      start: el("f-start").value,
      end: el("f-end").value,
      activity: el("f-activity").value,
      teacher: el("f-teacher").value,
      notes: el("f-notes").value,
    };
    if (!bookingId && el("f-repeat").checked) {
      payload.repeat = "weekly";
      payload.repeat_until = el("f-repeat-until").value;
      payload.repeat_weekdays = [...document.querySelectorAll(".weekday-picks input:checked")]
        .map((c) => Number(c.value));
      if (!payload.repeat_until) { showError("Choose an end date for the repeat."); return; }
    }

    const resp = await fetch(bookingId ? `/api/bookings/${bookingId}` : "/api/bookings", {
      method: bookingId ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) { showError(data.error || "Something went wrong."); return; }
    if (data.skipped && data.skipped.length) {
      alert("Booked, but these dates were skipped (already booked):\n" + data.skipped.join("\n"));
    }
    location.reload();
  });

  // Jump-to-date picker in the week nav.
  const jump = document.getElementById("jump-date");
  if (jump) jump.addEventListener("change", () => {
    if (jump.value) location.href = `/week/${jump.value}`;
  });
})();

from datetime import date, datetime, time, timedelta

from flask import (Blueprint, jsonify, redirect, render_template, request,
                   session, url_for)

from .auth import login_required
from .models import (Booking, BookingSeries, Room, audit, db, find_conflicts,
                     slot_label, slot_starts)

bp = Blueprint("main", __name__)

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def parse_time(s):
    return datetime.strptime(s, "%H:%M").time()


def monday_of(d):
    return d - timedelta(days=d.weekday())


@bp.route("/")
@login_required
def index():
    return redirect(url_for("main.week", day=date.today().isoformat()))


@bp.route("/week/<day>")
@login_required
def week(day):
    try:
        anchor = date.fromisoformat(day)
    except ValueError:
        return redirect(url_for("main.index"))

    monday = monday_of(anchor)
    days = [monday + timedelta(days=i) for i in range(5)]
    rooms = (Room.query.filter_by(active=True)
             .order_by(Room.sort_order, Room.name).all())
    slots = slot_starts()

    week_bookings = (Booking.query
                     .filter(Booking.date >= days[0], Booking.date <= days[-1])
                     .order_by(Booking.start_time).all())
    by_room_day = {}
    for b in week_bookings:
        by_room_day.setdefault((b.room_id, b.date), []).append(b)

    # For each day/room build a list of cells: either a free slot or a
    # booking spanning N slots — drives colspan in the template.
    grid = {}
    for d in days:
        for room in rooms:
            cells = []
            bookings = by_room_day.get((room.id, d), [])
            i = 0
            while i < len(slots):
                slot = slots[i]
                booking = next((b for b in bookings
                                if b.start_time <= slot < b.end_time), None)
                if booking:
                    span = sum(1 for s in slots[i:] if s < booking.end_time)
                    cells.append({"booking": booking, "span": span})
                    i += span
                else:
                    cells.append({"booking": None, "slot": slot})
                    i += 1
            grid[(d, room.id)] = cells

    return render_template(
        "week.html",
        days=days, rooms=rooms, slots=slots, grid=grid,
        slot_label=slot_label,
        monday=monday,
        prev_week=(monday - timedelta(days=7)).isoformat(),
        next_week=(monday + timedelta(days=7)).isoformat(),
        today=date.today(),
        user=session.get("user"),
    )


@bp.route("/api/bookings", methods=["POST"])
@login_required
def create_booking():
    data = request.get_json(force=True)
    user = session["user"]["name"]
    try:
        room_id = int(data["room_id"])
        start_date = date.fromisoformat(data["date"])
        start = parse_time(data["start"])
        end = parse_time(data["end"])
        activity = data["activity"].strip()
    except (KeyError, ValueError):
        return jsonify(error="Missing or invalid fields."), 400
    if not activity:
        return jsonify(error="Course / activity is required."), 400
    if end <= start:
        return jsonify(error="End time must be after start time."), 400
    if not Room.query.get(room_id):
        return jsonify(error="Unknown room."), 400

    common = dict(
        room_id=room_id, start_time=start, end_time=end, activity=activity,
        teacher=data.get("teacher", "").strip() or None,
        notes=data.get("notes", "").strip() or None,
        booked_by=user,
    )

    # Build the list of dates: single, or weekly repeats until a given date.
    dates = [start_date]
    series = None
    if data.get("repeat") == "weekly":
        try:
            until = date.fromisoformat(data["repeat_until"])
            weekdays = [int(w) for w in data.get("repeat_weekdays", [])]
        except (KeyError, ValueError):
            return jsonify(error="Repeat needs weekdays and an end date."), 400
        if not weekdays:
            weekdays = [start_date.weekday()]
        if until < start_date:
            return jsonify(error="Repeat end date is before the start."), 400
        if (until - start_date).days > 370:
            return jsonify(error="Repeat range is limited to one year."), 400
        dates = [start_date + timedelta(days=i)
                 for i in range((until - start_date).days + 1)
                 if (start_date + timedelta(days=i)).weekday() in weekdays]
        series = BookingSeries(
            weekdays=",".join(str(w) for w in sorted(set(weekdays))),
            until=until, created_by=user)
        db.session.add(series)

    created, skipped = [], []
    for d in dates:
        if find_conflicts(room_id, d, start, end):
            skipped.append(d.isoformat())
            continue
        b = Booking(date=d, series=series, **common)
        db.session.add(b)
        created.append(b)
    if not created:
        db.session.rollback()
        return jsonify(error="That slot is already booked."
                       if len(dates) == 1 else
                       "All requested dates clash with existing bookings: "
                       + ", ".join(skipped)), 409

    db.session.flush()
    for b in created:
        audit(user, "create", b.id, b.as_dict())
    db.session.commit()
    return jsonify(created=len(created), skipped=skipped), 201


@bp.route("/api/bookings/<int:booking_id>", methods=["GET", "PUT"])
@login_required
def booking_detail(booking_id):
    b = Booking.query.get_or_404(booking_id)
    if request.method == "GET":
        return jsonify(b.as_dict())

    # PUT — anyone signed in may edit; deleting is not allowed.
    data = request.get_json(force=True)
    user = session["user"]["name"]
    before = b.as_dict()
    try:
        b.room_id = int(data.get("room_id", b.room_id))
        b.date = date.fromisoformat(data.get("date", b.date.isoformat()))
        b.start_time = parse_time(data.get("start", b.start_time.strftime("%H:%M")))
        b.end_time = parse_time(data.get("end", b.end_time.strftime("%H:%M")))
    except ValueError:
        return jsonify(error="Invalid date or time."), 400
    if "activity" in data:
        if not data["activity"].strip():
            return jsonify(error="Course / activity is required."), 400
        b.activity = data["activity"].strip()
    if "teacher" in data:
        b.teacher = data["teacher"].strip() or None
    if "notes" in data:
        b.notes = data["notes"].strip() or None
    if b.end_time <= b.start_time:
        return jsonify(error="End time must be after start time."), 400
    if find_conflicts(b.room_id, b.date, b.start_time, b.end_time, exclude_id=b.id):
        return jsonify(error="That slot is already booked."), 409

    audit(user, "edit", b.id, {"before": before, "after": b.as_dict()})
    db.session.commit()
    return jsonify(b.as_dict())


@bp.route("/search")
@login_required
def search():
    q = request.args.get("q", "").strip()
    results = []
    if q:
        like = f"%{q}%"
        results = (Booking.query
                   .filter(db.or_(Booking.activity.ilike(like),
                                  Booking.teacher.ilike(like),
                                  Booking.booked_by.ilike(like),
                                  Booking.notes.ilike(like)))
                   .order_by(Booking.date, Booking.start_time)
                   .limit(300).all())
    return render_template("search.html", q=q, results=results,
                           user=session.get("user"))


@bp.route("/rooms", methods=["GET", "POST"])
@login_required
def rooms():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        capacity = request.form.get("capacity", "").strip()
        if name and not Room.query.filter_by(name=name).first():
            db.session.add(Room(name=name,
                                capacity=int(capacity) if capacity.isdigit() else None,
                                sort_order=(db.session.query(
                                    db.func.coalesce(db.func.max(Room.sort_order), 0)
                                ).scalar() or 0) + 1))
            db.session.commit()
        return redirect(url_for("main.rooms"))
    all_rooms = Room.query.order_by(Room.sort_order, Room.name).all()
    return render_template("rooms.html", rooms=all_rooms,
                           user=session.get("user"))


@bp.route("/rooms/<int:room_id>/toggle", methods=["POST"])
@login_required
def toggle_room(room_id):
    room = Room.query.get_or_404(room_id)
    room.active = not room.active
    db.session.commit()
    return redirect(url_for("main.rooms"))

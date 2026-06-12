import json
from datetime import datetime, time, timedelta

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# The bookable day: 30-minute slots from 09:00 to 17:00, where the final
# "17:00+" slot represents 17:00 onwards (stored internally as 17:00-18:00).
DAY_START = time(9, 0)
DAY_END = time(18, 0)
SLOT_MINUTES = 30


def slot_starts():
    """All slot start times for one day: 09:00, 09:30, ... 17:00."""
    slots = []
    t = datetime(2000, 1, 1, DAY_START.hour, DAY_START.minute)
    end = datetime(2000, 1, 1, DAY_END.hour, DAY_END.minute)
    while t < end:
        slots.append(t.time())
        t += timedelta(minutes=SLOT_MINUTES)
    return slots


def slot_label(t):
    return "17:00+" if t == time(17, 0) else t.strftime("%H:%M")


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    capacity = db.Column(db.Integer)
    sort_order = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True, nullable=False)

    bookings = db.relationship("Booking", back_populates="room")

    @property
    def display_name(self):
        return f"{self.name} ({self.capacity})" if self.capacity else self.name


class BookingSeries(db.Model):
    """A weekly repeat rule. Individual occurrences are Booking rows."""
    id = db.Column(db.Integer, primary_key=True)
    weekdays = db.Column(db.String(20), nullable=False)  # e.g. "0,1" = Mon,Tue
    until = db.Column(db.Date, nullable=False)
    created_by = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship("Booking", back_populates="series")


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    activity = db.Column(db.String(200), nullable=False)  # course code / event
    teacher = db.Column(db.String(200))                   # who is teaching / who it's for
    booked_by = db.Column(db.String(200))
    notes = db.Column(db.Text)
    series_id = db.Column(db.Integer, db.ForeignKey("booking_series.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    room = db.relationship("Room", back_populates="bookings")
    series = db.relationship("BookingSeries", back_populates="bookings")

    __table_args__ = (db.Index("ix_booking_room_date", "room_id", "date"),)

    def as_dict(self):
        return {
            "id": self.id,
            "room_id": self.room_id,
            "room": self.room.display_name,
            "date": self.date.isoformat(),
            "start": self.start_time.strftime("%H:%M"),
            "end": self.end_time.strftime("%H:%M"),
            "activity": self.activity,
            "teacher": self.teacher or "",
            "booked_by": self.booked_by or "",
            "notes": self.notes or "",
            "series_id": self.series_id,
        }


def find_conflicts(room_id, date, start, end, exclude_id=None):
    """Bookings in the same room/date overlapping [start, end)."""
    q = Booking.query.filter(
        Booking.room_id == room_id,
        Booking.date == date,
        Booking.start_time < end,
        Booking.end_time > start,
    )
    if exclude_id:
        q = q.filter(Booking.id != exclude_id)
    return q.all()


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user = db.Column(db.String(200))
    action = db.Column(db.String(20), nullable=False)  # create / edit / import
    booking_id = db.Column(db.Integer)
    details = db.Column(db.Text)


def audit(user, action, booking_id, details):
    db.session.add(AuditLog(
        user=user, action=action, booking_id=booking_id,
        details=json.dumps(details, default=str),
    ))

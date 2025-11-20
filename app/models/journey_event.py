from datetime import datetime
from app.extensions import db

ALLOWED_JOURNEY_TYPES = {"출발", "도착"}

class JourneyEvent(db.Model):
    __tablename__ = 'journey_events'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    event_type = db.Column(db.String(16), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'event_type': self.event_type,
            'created_at': self.created_at.isoformat(),
        }

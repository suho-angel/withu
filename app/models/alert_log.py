from datetime import datetime
from app.extensions import db

ALLOWED_ALERT_REASONS = {"경로이탈", "위험음 감지", "도착 지연"}

class AlertLog(db.Model):
    __tablename__ = 'alert_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    reason = db.Column(db.String(32), nullable=False, index=True)
    recipients = db.Column(db.JSON, nullable=False)  # [{relation, name, phone}]
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'reason': self.reason,
            'recipients': self.recipients,
            'recipients_count': len(self.recipients) if isinstance(self.recipients, list) else 0,
            'created_at': self.created_at.isoformat(),
        }

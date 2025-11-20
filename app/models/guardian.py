from datetime import datetime
from app.extensions import db

ALLOWED_RELATIONS = {'엄마', '아빠', '형제', '친구', '기타'}

class Guardian(db.Model):
    __tablename__ = 'guardians'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    relation = db.Column(db.String(16), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    phone = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'phone', name='uq_user_phone'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'relation': self.relation,
            'name': self.name,
            'phone': self.phone,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

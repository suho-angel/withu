from datetime import datetime
from app.extensions import db

ALLOWED_GENDERS = {'남', '여', '기타'}

class UserProfile(db.Model):
    __tablename__ = 'user_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    gender = db.Column(db.String(8), nullable=True)
    name = db.Column(db.String(64), nullable=True)
    birth_year = db.Column(db.Integer, nullable=True)
    phone = db.Column(db.String(32), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'gender': self.gender,
            'name': self.name,
            'birth_year': self.birth_year,
            'phone': self.phone,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

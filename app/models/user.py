from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from sqlalchemy.orm import relationship
from .guardian import Guardian
from .user_profile import UserProfile

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # EmailVerification 관계 제거: 가입 시점 = 인증 시점 간주
    # Cascade 삭제: User 삭제 시 관련 Guardian/UserProfile 자동 제거
    contacts = relationship(
        'Guardian', backref='user', lazy='dynamic', cascade='all, delete-orphan'
    )
    profile = relationship(
        'UserProfile', backref='user', uselist=False, lazy='joined', cascade='all, delete-orphan'
    )

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        # 이메일 인증을 별도 저장하지 않으므로 가입된 모든 사용자 verified=True 처리
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'verified': True,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

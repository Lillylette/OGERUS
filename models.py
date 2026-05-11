from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256))
    avatar = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class UserProgress(db.Model):
    __tablename__ = 'user_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    topic_id = db.Column(db.Integer, nullable=False)
    topic_name = db.Column(db.String(200))
    skill = db.Column(db.String(100))
    total_attempts = db.Column(db.Integer, default=0)
    correct_attempts = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref=db.backref('progress', lazy='dynamic'))


class ChecklistItem(db.Model):
    __tablename__ = 'checklist_items'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    topic_id = db.Column(db.Integer, nullable=False)
    topic_name = db.Column(db.String(200))
    checked = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref=db.backref('checklist_items', lazy='dynamic'))


class UserAchievement(db.Model):
    __tablename__ = 'user_achievements'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    achievement_id = db.Column(db.Integer, nullable=False)
    achievement_name = db.Column(db.String(100))
    achievement_description = db.Column(db.String(300))
    icon = db.Column(db.String(50))

    user = db.relationship('User', backref=db.backref('achievements', lazy='dynamic'))
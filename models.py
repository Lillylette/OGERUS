from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    avatar = db.Column(db.String(500), default='/static/uploads/default_avatar.png')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)


class UserProgress(db.Model):
    __tablename__ = 'user_progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    topic_id = db.Column(db.Integer, nullable=False)
    topic_name = db.Column(db.String(200), nullable=False)
    skill = db.Column(db.String(50), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    correct_attempts = db.Column(db.Integer, default=0)
    total_attempts = db.Column(db.Integer, default=0)
    last_practiced = db.Column(db.DateTime, default=datetime.utcnow)


class ChecklistItem(db.Model):
    __tablename__ = 'checklist_items'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    topic_id = db.Column(db.Integer, nullable=False)
    topic_name = db.Column(db.String(200), nullable=False)
    checked = db.Column(db.Boolean, default=False)


class UserAchievement(db.Model):
    __tablename__ = 'user_achievements'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    achievement_id = db.Column(db.Integer, nullable=False)
    achievement_name = db.Column(db.String(100), nullable=False)
    achievement_description = db.Column(db.String(300))
    icon = db.Column(db.String(200))
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
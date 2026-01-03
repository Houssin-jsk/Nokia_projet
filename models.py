import os
import random
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


PROGRESS_LABELS = {
    0: "Not started",
    1: "Reading document & understanding my character",
    2: "Collecting notes and resources",
    3: "Structuring my slides",
    4: "Polishing my slides and timing",
    5: "Ready to present",
}


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    title = db.Column(db.String(120), nullable=False)
    angle = db.Column(db.String(255), nullable=False)
    key_message = db.Column(db.String(255), nullable=False)
    bullet_points = db.Column(db.Text, nullable=False)

    users = db.relationship("User", back_populates="role")


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), unique=True, nullable=False)
    access_code = db.Column(db.String(64), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), nullable=True)
    progress_step = db.Column(db.Integer, default=0)
    last_login_at = db.Column(db.DateTime, nullable=True)
    last_seen_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    is_ppt_owner = db.Column(db.Boolean, default=False)

    role = db.relationship("Role", back_populates="users")
    notes = db.relationship("Note", back_populates="user", cascade="all, delete-orphan")
    resources = db.relationship("ResourceFile", back_populates="user", cascade="all, delete-orphan")
    messages = db.relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")

    @property
    def progress_label(self):
        return PROGRESS_LABELS.get(self.progress_step, "Not started")


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", back_populates="notes")


class ResourceFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=True)
    original_filename = db.Column(db.String(255), nullable=True)
    file_type = db.Column(db.String(32), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="resources")


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="messages")


ROLES_DATA = [
    {
        "code": "CEO",
        "title": "PDG / Direction géérale",
        "angle": "Strategic decisions and speed of reaction.",
        "key_message": "Nokia moved too slowly to the smartphone revolution and lost focus.",
        "bullet_points": "\n".join(
            [
                "After the iPhone, the market moved to touch, UX, and apps.",
                "Too many platforms (Symbian, MeeGo, S40) created confusion and fragmentation.",
                "Major strategic shifts came too late.",
                "The Microsoft alliance increased dependence while the apps ecosystem was still weak.",
            ]
        ),
    },
    {
        "code": "PM",
        "title": "Product Manager",
        "angle": "Product–market fit.",
        "key_message": "The products no longer matched what users expected from modern smartphones.",
        "bullet_points": "\n".join(
            [
                "Users valued simplicity, fluid touch experience, and coherence across models.",
                "Symbian was not designed as a native touch-first OS.",
                "Too many device variants made it hard to deliver a consistent UX.",
                "Nokia struggled to match the speed of iOS/Android feature delivery.",
            ]
        ),
    },
    {
        "code": "ENGINEER",
        "title": "Ingénieur·e Symbian",
        "angle": "Technical debt and architecture limits.",
        "key_message": "The legacy software base was too heavy and slow to evolve.",
        "bullet_points": "\n".join(
            [
                "Architecture came from a pre-smartphone era.",
                "Fragmentation made performance and stability harder to guarantee.",
                "Release cycles were slow, causing constant delays.",
                "Testing across many versions and devices was costly.",
            ]
        ),
    },
    {
        "code": "DESIGNER",
        "title": "Designer UX/UI",
        "angle": "User experience and perception of modernity.",
        "key_message": "Even with features, a weak UX made Nokia look behind competitors.",
        "bullet_points": "\n".join(
            [
                "People compared smoothness, not just feature lists.",
                "Navigation was inconsistent across devices.",
                "No strong, unified UX identity across the range.",
                "Touch design must be native: gestures, typography, spacing, transitions.",
            ]
        ),
    },
    {
        "code": "DEV",
        "title": "Développeur·se d’applications",
        "angle": "Apps and developer ecosystem.",
        "key_message": "Developers go where tools, monetization, and audience are best.",
        "bullet_points": "\n".join(
            [
                "Tools and docs were less attractive than on iOS/Android.",
                "Monetization and audience size were unclear for Nokia’s platforms.",
                "Fewer apps led to fewer users, creating a negative network effect.",
                "App stores and ecosystems became a major competitive advantage.",
            ]
        ),
    },
    {
        "code": "SALES",
        "title": "Responsable Ventes / Opérateurs",
        "angle": "Market demand and distribution.",
        "key_message": "Customers and operators pushed iPhone/Android as the new premium standard.",
        "bullet_points": "\n".join(
            [
                "High-end competition became about ecosystems, not only hardware.",
                "Hard to convince people in stores when OS and apps looked behind.",
                "Marketing and buzz moved to iOS and Android.",
                "Less high-end sales reduced margins and investment capacity.",
            ]
        ),
    },
    {
        "code": "COMPETITOR",
        "title": "Voix du concurrent (Apple/Android)",
        "angle": "Why the other side won.",
        "key_message": "Competitors combined fast iteration, strong UX, and a powerful apps platform.",
        "bullet_points": "\n".join(
            [
                "Touch-first OS and coherent end-to-end experience.",
                "Strong app store, good tools, and a large developer community.",
                "Fast updates and continuous improvements.",
                "Clear positioning: one vision, one OS, one message.",
            ]
        ),
    },
]


USERS_DATA = [
    {"full_name": "Aoudani", "access_code": "AOU2025"},
    {"full_name": "El Houssaine", "access_code": "HOU2025"},
    {"full_name": "Amin", "access_code": "AMI2025"},
    {"full_name": "Nour", "access_code": "NOU2025"},
    {"full_name": "Naoual", "access_code": "NAO2025"},
    {"full_name": "Wasima", "access_code": "WAS2025"},
    {"full_name": "Israe", "access_code": "ISR2025"},
    {"full_name": "Admin PIE", "access_code": "ADMIN2025", "is_admin": True},
]


def init_db(app):
    db_path = app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    db.create_all()

    if Role.query.count() == 0:
        for role in ROLES_DATA:
            db.session.add(Role(**role))
        db.session.commit()

    if User.query.count() == 0:
        for data in USERS_DATA:
            db.session.add(User(**data))
        db.session.commit()


def assign_random_role(user):
    if user.role_id:
        return

    assigned_role_ids = {u.role_id for u in User.query.filter(User.role_id.isnot(None)).all()}
    free_roles = Role.query.filter(~Role.id.in_(assigned_role_ids)).all() if assigned_role_ids else Role.query.all()

    if not free_roles:
        return

    chosen = random.choice(free_roles)
    user.role = chosen
    db.session.commit()

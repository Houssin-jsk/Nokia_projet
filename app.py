import os
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from forms import ChatForm, FileUploadForm, LinkResourceForm, LoginForm, NoteForm, ProgressForm
from models import (
    ChatMessage,
    Note,
    PROGRESS_LABELS,
    ResourceFile,
    Role,
    User,
    assign_random_role,
    db,
    init_db,
)


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"pdf", "docx", "pptx", "xlsx", "txt"}
STICKER_MAP = {
    ":idea:": "idea.svg",
    ":panic:": "panic.svg",
    ":team:": "team.svg",
    ":deadline:": "deadline.svg",
}
EMOJIS = ["😀", "😅", "😂", "🤔", "😎", "💡", "✅", "📌", "🔥"]


app = Flask(__name__)
app.config["SECRET_KEY"] = "nokia-secret-pie"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///nokia_lab.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db.init_app(app)
with app.app_context():
    init_db(app)


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


@app.before_request
def update_last_seen():
    user_id = session.get("user_id")
    if user_id:
        user = User.query.get(user_id)
        if user and not user.is_admin:
            now = datetime.utcnow()
            if not user.last_seen_at or (now - user.last_seen_at) > timedelta(minutes=1):
                user.last_seen_at = now
                db.session.commit()


@app.context_processor
def inject_user():
    return {"current_user": get_current_user()}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if not user or not user.is_admin:
            return render_template("unauthorized.html"), 403
        return view(*args, **kwargs)

    return wrapped


def compute_team_overview():
    team = User.query.filter_by(is_admin=False).order_by(User.full_name).all()
    progress_counts = {step: 0 for step in PROGRESS_LABELS}
    assigned_roles = 0
    total_progress = 0

    for teammate in team:
        step_value = teammate.progress_step if teammate.progress_step in PROGRESS_LABELS else 0
        progress_counts[step_value] = progress_counts.get(step_value, 0) + 1
        if teammate.role_id:
            assigned_roles += 1
        total_progress += teammate.progress_step or 0

    ordered_steps = sorted(PROGRESS_LABELS.items())
    progress_labels = [label for _, label in ordered_steps]
    progress_values = [progress_counts.get(step, 0) for step, _ in ordered_steps]
    unassigned_roles = len(team) - assigned_roles
    max_progress = (len(team) * 5) or 1
    avg_progress_pct = (total_progress / max_progress) * 100 if team else 0

    return {
        "team": team,
        "progress_labels": progress_labels,
        "progress_values": progress_values,
        "assigned_count": assigned_roles,
        "unassigned_count": unassigned_roles,
        "avg_progress_pct": avg_progress_pct,
        "student_count": len(team),
    }


@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("home"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    form = LoginForm()
    users = User.query.order_by(User.full_name).all()
    form.full_name.choices = [(u.full_name, u.full_name) for u in users]

    if form.validate_on_submit():
        user = User.query.filter_by(full_name=form.full_name.data).first()
        if user and user.access_code == form.access_code.data:
            session["user_id"] = user.id
            user.last_login_at = datetime.utcnow()
            db.session.commit()
            assign_random_role(user)
            flash("Logged in successfully.", "success")
            return redirect(url_for("home"))
        flash("Invalid name or access code.", "danger")

    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("login"))


@app.route("/home")
@login_required
def home():
    stats = compute_team_overview()
    logged_in_users = User.query.filter(User.last_login_at.isnot(None)).count()
    ppt_owner = User.query.filter_by(is_ppt_owner=True).first()
    return render_template(
        "home.html",
        stats=stats,
        logged_in_users=logged_in_users,
        ppt_owner=ppt_owner,
    )


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    user = get_current_user()
    progress_form = ProgressForm(progress_step=user.progress_step)
    ppt_owner = User.query.filter_by(is_ppt_owner=True).first()

    if progress_form.validate_on_submit():
        user.progress_step = progress_form.progress_step.data
        db.session.commit()
        flash("Progress updated.", "success")
        return redirect(url_for("dashboard"))

    stats = compute_team_overview()
    now = datetime.utcnow()
    team_rows = []
    ten_minutes = timedelta(minutes=10)
    for teammate in stats["team"]:
        initials = "".join([part[0] for part in teammate.full_name.split()[:2]]).upper()
        is_online = teammate.last_seen_at and (now - teammate.last_seen_at) <= ten_minutes
        team_rows.append(
            {
                "id": teammate.id,
                "full_name": teammate.full_name,
                "initials": initials,
                "role": teammate.role.title if teammate.role else "Not assigned yet",
                "role_progress": f"{teammate.role.title if teammate.role else 'Not assigned yet'} – {teammate.progress_label}",
                "progress": teammate.progress_label,
                "is_online": is_online,
            }
        )

    return render_template(
        "dashboard.html",
        progress_form=progress_form,
        team_rows=team_rows,
        progress_labels=stats["progress_labels"],
        progress_values=stats["progress_values"],
        assigned_count=stats["assigned_count"],
        unassigned_count=stats["unassigned_count"],
        ppt_owner=ppt_owner,
        student_count=stats["student_count"],
    )


@app.route("/resources", methods=["GET", "POST"])
@login_required
def resources():
    user = get_current_user()
    note_form = NoteForm()
    file_form = FileUploadForm()
    link_form = LinkResourceForm()

    handled = False

    if note_form.submit_note.data and note_form.validate_on_submit():
        note = Note(user=user, title=note_form.title.data, content=note_form.content.data)
        db.session.add(note)
        db.session.commit()
        flash("Note saved.", "success")
        handled = True

    elif file_form.submit_file.data and request.method == "POST":
        uploaded_file = file_form.file.data
        if not uploaded_file:
            flash("Please choose a file to upload.", "warning")
        else:
            filename = secure_filename(uploaded_file.filename or "")
            if not filename:
                flash("Invalid filename.", "warning")
            else:
                ext = filename.rsplit(".", 1)[-1].lower()
                if ext not in ALLOWED_EXTENSIONS:
                    flash("File type not allowed.", "danger")
                else:
                    stored_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{filename}"
                    path = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)
                    uploaded_file.save(path)
                    resource = ResourceFile(
                        user=user,
                        filename=stored_name,
                        original_filename=filename,
                        file_type=ext,
                        description=file_form.description.data,
                    )
                    db.session.add(resource)
                    db.session.commit()
                    flash("File uploaded.", "success")
                    handled = True

    elif link_form.submit_link.data and link_form.validate_on_submit():
        resource = ResourceFile(
            user=user,
            filename=None,
            original_filename=None,
            file_type="link",
            description=link_form.description.data,
            url=link_form.url.data,
        )
        db.session.add(resource)
        db.session.commit()
        flash("Link saved.", "success")
        handled = True

    if handled:
        return redirect(url_for("resources"))

    my_notes = Note.query.filter_by(user_id=user.id).order_by(Note.updated_at.desc()).all()
    my_files = ResourceFile.query.filter_by(user_id=user.id).order_by(ResourceFile.created_at.desc()).all()
    all_resources = ResourceFile.query.order_by(ResourceFile.created_at.desc()).all()

    return render_template(
        "resources.html",
        note_form=note_form,
        file_form=file_form,
        link_form=link_form,
        my_notes=my_notes,
        my_files=my_files,
        all_resources=all_resources,
    )


@app.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    form = ChatForm()
    user = get_current_user()

    if form.validate_on_submit():
        message = ChatMessage(user=user, content=form.content.data)
        db.session.add(message)
        db.session.commit()
        return redirect(url_for("chat"))

    messages = ChatMessage.query.order_by(ChatMessage.created_at.asc()).all()
    return render_template("chat.html", form=form, messages=messages, stickers=STICKER_MAP, emojis=EMOJIS)


@app.route("/admin/users", methods=["GET", "POST"])
@admin_required
def admin_users():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        action = request.form.get("action")
        user = User.query.get(user_id)
        if not user:
            flash("User not found.", "danger")
        elif action == "reset":
            user.role_id = None
            user.progress_step = 0
            db.session.commit()
            flash(f"Reset done for {user.full_name}.", "info")
        elif action == "remove_ppt":
            if user.is_ppt_owner:
                user.is_ppt_owner = False
                db.session.commit()
                flash(f"{user.full_name} is no longer the PPT owner.", "info")
            else:
                flash("Selected user is not the PPT owner.", "warning")
        return redirect(url_for("admin_users"))

    users = User.query.order_by(User.full_name).all()
    return render_template("admin_users.html", users=users)


@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=False)


@app.route("/claim-ppt", methods=["POST"])
@login_required
def claim_ppt():
    user = get_current_user()
    existing_owner = User.query.filter_by(is_ppt_owner=True).first()
    if existing_owner and existing_owner.id != user.id:
        flash("Someone else already took the PPT role.", "warning")
    elif existing_owner and existing_owner.id == user.id:
        flash("You are already the PPT owner.", "info")
    else:
        user.is_ppt_owner = True
        db.session.commit()
        flash("You are now the PPT owner.", "success")
    return redirect(url_for("dashboard"))


@app.route("/ppt-resources")
@login_required
def ppt_resources():
    user = get_current_user()
    if not user.is_ppt_owner:
        flash("This area is reserved for the PPT owner.", "warning")
        return redirect(url_for("dashboard"))
    notes = Note.query.order_by(Note.updated_at.desc()).all()
    resources = ResourceFile.query.order_by(ResourceFile.created_at.desc()).all()
    return render_template("ppt_resources.html", notes=notes, resources=resources)


@app.errorhandler(404)
def not_found(_):
    return render_template("not_found.html"), 404


@app.errorhandler(403)
def forbidden(_):
    return render_template("unauthorized.html"), 403


if __name__ == "__main__":
    app.run(debug=True)

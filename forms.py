from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, PasswordField, TextAreaField, FileField, SubmitField
from wtforms.validators import DataRequired, Length, URL


class LoginForm(FlaskForm):
    full_name = SelectField("Full Name", validators=[DataRequired()])
    access_code = PasswordField("Access Code", validators=[DataRequired(), Length(min=4, max=32)])
    submit = SubmitField("Log In")


class ProgressForm(FlaskForm):
    progress_step = SelectField(
        "Progress",
        coerce=int,
        choices=[
            (0, "Not started"),
            (1, "Reading document & understanding my character"),
            (2, "Collecting notes and resources"),
            (3, "Structuring my slides"),
            (4, "Polishing my slides and timing"),
            (5, "Ready to present"),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField("Update")


class NoteForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=150)])
    content = TextAreaField("Content", validators=[DataRequired()])
    submit_note = SubmitField("Save Note")


class FileUploadForm(FlaskForm):
    file = FileField("File")
    description = StringField("Description", validators=[Length(max=255)])
    submit_file = SubmitField("Upload File")


class LinkResourceForm(FlaskForm):
    url = StringField("URL", validators=[DataRequired(), URL()])
    description = StringField("Description", validators=[Length(max=255)])
    submit_link = SubmitField("Save Link")


class ChatForm(FlaskForm):
    content = TextAreaField("Message", validators=[DataRequired(), Length(max=1000)])
    submit_chat = SubmitField("Send")

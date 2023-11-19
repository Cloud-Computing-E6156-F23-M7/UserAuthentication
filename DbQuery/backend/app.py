import json, os, re
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

### Set up the databases ###

class DbConfig(object):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site_mgmt.db'
    SQLALCHEMY_BINDS = {
        'sitemgmt_db': SQLALCHEMY_DATABASE_URI,  # default bind
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False


app = Flask(__name__)
app.config.from_object(DbConfig)
app.json.sort_keys = False
db = SQLAlchemy(app)
CORS(app)


class Admin(db.Model):
    __bind_key__ = 'sitemgmt_db'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    isDeleted = db.Column(db.Integer, default=False, nullable=False)  # soft deletion only

    actions = db.relationship('Action', back_populates='admin')


class Feedback(db.Model):
    __bind_key__ = 'sitemgmt_db'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    text = db.Column(db.Text, nullable=False)
    submission_date = db.Column(db.DateTime(timezone=True), default=func.now())
    isDeleted = db.Column(db.Integer, default=False, nullable=False)  # soft deletion only

    actions = db.relationship('Action', back_populates='feedback')


class Action(db.Model):
    # __tablename__ = 'action'
    __bind_key__ = 'sitemgmt_db'
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=False)
    feedback_id = db.Column(db.Integer, db.ForeignKey('feedback.id'), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    action_date = db.Column(db.DateTime(timezone=True), default=func.now())

    admin = db.relationship('Admin', back_populates='actions')
    feedback = db.relationship('Feedback', back_populates='actions')


# NOTE: This route is needed for the default EB health check route
@app.route('/')
def home():
    return "Ok"


### Reset database ###

@app.route('/api/reset/sitemgmt/', methods=['PUT'])
def reset_sitemgmt_db():
    engine = db.get_engine(app, bind='sitemgmt_db')
    if engine:
        metadata = db.MetaData()
        metadata.reflect(bind=engine)
        metadata.drop_all(bind=engine)
        metadata.create_all(bind=engine)
        return "Successfully reset the sitemgmt database"
    else:
        return "Error resetting the sitemgmt database", 501

### Admin resource ###

@app.route('/api/admin/', methods=['GET'])
def get_all_admin():
    admin_list = Admin.query.all()

    admins = [{
        'admin_id': admin.id,
        'email': admin.email,
        'isDeleted': admin.isDeleted
    } for admin in admin_list]

    return jsonify(admins)


@app.route('/api/admin/<string:admin_email>/', methods=['GET'])
def get_admin(admin_email):
    admin = Admin.query.filter_by(email=admin_email).first()

    if not admin:
        return "Admin not found", 404
    if admin.isDeleted == True:
        return "Admin not activated", 400

    admin_dic = {
        'admin_id': admin.id,
        'email': admin.email,
        'isDeleted': admin.isDeleted
    }

    return jsonify(admin_dic)


@app.route('/api/admin/', methods=['POST'])
def add_admin(user):
    # email = request.json.get('email')

    email = user["email"]

    if email is None:
        return "Email cannot be null", 400

    admin = Admin.query.filter_by(email=email).first()

    if not admin:
        new_admin = Admin(email=email)
        db.session.add(new_admin)
        db.session.commit()
        return "Successfully added an admin", 201
    else:
        if admin.isDeleted == True:
            admin.isDeleted = False
            db.session.commit()
            return "Successfully reactivated a deleted admin"
        else:
            return "admin already exists and is activated", 400


@app.route('/api/admin/<string:admin_email>/', methods=['DELETE'])
def delete_admin(admin_email):
    admin = Admin.query.filter_by(id=admin_id).first()

    if admin:
        admin.isDeleted = True
        try:
            db.session.commit()
            return "Successfully deactivated an admin"
        except (IntegrityError, SQLAlchemyError):
            db.session.rollback()
            return "Error deactivating an admin", 501
    else:
        return "Admin not found", 404


@app.route('/api/admin/<string:admin_email>/', methods=['PUT'])
def update_admin(admin_email):
    admin = Admin.query.filter_by(email=admin_email).first()
    new_email = request.json.get('email')

    if admin:
        if not new_email:
            if admin.isDeleted == True:
                admin.isDeleted = False
                db.session.commit()
                return "Successfully reactivated a deleted admin"
            else:
                return "Email cannot be null", 400
        if Admin.query.filter_by(email=new_email).first():
            return "Email already exists", 400
        admin.email = new_email
        if admin.isDeleted == True:
            admin.isDeleted = False
            db.session.commit()
            return "Successfully activated an admin and updated the email"
        else:
            db.session.commit()
            return "Successfully updated an admin email"
    else:
        return "Admin not found", 404


### Feedback resource ###

@app.route('/api/feedback/', methods=['POST'])
def submit_feedback():
    feedback_data = request.get_json()

    feedback_text = feedback_data.get('text')

    if feedback_text is None:
        return "Text cannot be null", 400

    new_feedback = Feedback(
        name=feedback_data.get('name'),
        email=feedback_data.get('email'),
        text=feedback_text
    )

    db.session.add(new_feedback)
    db.session.commit()

    return "Successfully submitted feedback", 201


@app.route('/api/feedback/<int:feedback_id>/')
def get_feedback(feedback_id):
    feedback = Feedback.query.filter_by(id=feedback_id, isDeleted=False).first()

    if not feedback:
        return "Feedback not found or deleted", 404

    feedback_dic = {
        'feedback_id': feedback.id,
        'submission_date': feedback.submission_date,
        'name': feedback.name,
        'email': feedback.email,
        'text': feedback.text
    }

    return jsonify(feedback_dic)


@app.route('/api/feedback/<int:feedback_id>/', methods=['PUT'])
def update_feedback(feedback_id):
    feedback = Feedback.query.filter_by(id=feedback_id, isDeleted=False).first()

    if not feedback:
        return "Feedback not found or deleted", 404

    new_feedback_data = request.get_json()

    if not new_feedback_data:
        return "No data provided", 400

    feedback.name = new_feedback_data.get('name') if new_feedback_data.get('name') else feedback.name
    feedback.email = new_feedback_data.get('email') if new_feedback_data.get('email') else feedback.email
    new_text = new_feedback_data.get('text') if new_feedback_data.get('text') else feedback.text

    try:
        db.session.commit()
        return "Successfully updated feedback"
    except (IntegrityError, SQLAlchemyError):
        db.session.rollback()
        return "Error updating feedback", 501


@app.route('/api/feedback/<int:feedback_id>/', methods=['DELETE'])
def delete_feedback(feedback_id):
    feedback = Feedback.query.filter_by(id=feedback_id, isDeleted=False).first()

    if feedback:
        feedback.isDeleted = True
        feedback.name = '<Anonymized for deletion>'
        feedback.email = '<Anonymized for deletion>'
        try:
            db.session.commit()
            return "Successfully deleted feedback"
        except (IntegrityError, SQLAlchemyError):
            db.session.rollback()
            return "Error deleting feedback", 501
    else:
        return "Feedback not found or already deleted", 404


### Feedback resource only authorized for admin ###

@app.route('/api/admin/feedback/')
def get_all_feedback():
    feedback_list = db.session.query(Feedback, Action, Admin) \
        .select_from(Feedback) \
        .join(Action, isouter=True) \
        .join(Admin, isouter=True) \
        .all()

    feedback_entries = [{
        'feedback_id': feedback.id,
        'submission_date': feedback.submission_date,
        'name': feedback.name,
        'email': feedback.email,
        'text': feedback.text,
        'isDeleted': feedback.isDeleted,
        'actioned_by': admin.email if admin else None,
        'action_date': action.action_date if action else None,
        'action_comment': action.comment if action else None
    } for feedback, action, admin in feedback_list]

    return jsonify(feedback_entries)


### Action resource only authorized for admin ###

@app.route('/api/admin/action/')
def get_all_action():
    action_list = db.session.query(Action, Feedback, Admin) \
        .select_from(Action) \
        .join(Feedback, isouter=True) \
        .join(Admin, isouter=True) \
        .all()

    actions = [{
        'action_id': action.id,
        'admin': admin.email if admin else None,
        'action_date': action.action_date,
        'action_comment': action.comment,
        'feedback_id': feedback.id if feedback else None,
        'feedback_submission_date': feedback.submission_date if feedback else None,
        'feedback_name': feedback.name if feedback else None,
        'feedback_email': feedback.email if feedback else None,
        'feedback_text': feedback.text if feedback else None
    } for action, feedback, admin in action_list]

    return jsonify(actions)


@app.route('/api/admin/<int:admin_id>/feedback/<int:feedback_id>/', methods=['POST'])
def handle_feedback(admin_id, feedback_id):
    comment = request.json.get('comment')

    if not comment:
        return "Comment cannot be null", 400

    admin = Admin.query.filter_by(id=admin_id).first()

    if not (admin and Feedback.query.filter_by(id=feedback_id).first()):
        return "admin_id or feedback_id not found", 404

    if admin.isDeleted == True:
        return "admin is deactivated", 400

    new_action = Action(
        admin_id=admin_id,
        feedback_id=feedback_id,
        comment=comment
    )

    db.session.add(new_action)
    db.session.commit()

    return "Successfully logged a feedback action", 201


@app.route('/api/admin/action/<int:action_id>/', methods=['PUT'])
def update_action(action_id):
    action = Action.query.filter_by(id=action_id).first()

    if not action:
        return "Action not found", 404

    new_comment = request.json.get('comment')

    if not new_comment:
        return "Comment cannot be null", 400

    action.comment = new_comment

    try:
        db.session.commit()
        return "Successfully updated action"
    except (IntegrityError, SQLAlchemyError):
        db.session.rollback()
        return "Error updating action", 501


@app.route('/api/admin/action/<int:action_id>/', methods=['DELETE'])
def delete_action(action_id):
    action = Action.query.filter_by(id=action_id).first()

    if action:
        db.session.delete(action)
        try:
            db.session.commit()
            return "Successfully deleted action"
        except (IntegrityError, SQLAlchemyError):
            db.session.rollback()
            return "Error deleting action", 501
    else:
        return "Action not found", 404


def add_all_admins():
    arr = ["sz2803@columbia.edu", "kl3374@columbia.edu", "mb4753@columbia.edu", "nmz2117@columbia.edu",
           "mz2822@columbia.edu", "ma4265@columbia.edu", "sl5064@columbia.edu"]
    for email in arr:
        new_admin = Admin(email=email)
        db.session.add(new_admin)
        db.session.commit()
        return "Successfully added an admin", 201


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True, port=5000)

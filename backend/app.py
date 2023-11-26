import json
import os
import re
import boto3
import sqlite3
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, func, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.sql import func
from botocore.exceptions import NoCredentialsError, ClientError
from flask import jsonify, request

Base = declarative_base()

class Admin(Base):
    __tablename__ = 'admin'
    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True, nullable=False)
    isDeleted = Column(Integer, default=False, nullable=False)
    actions = relationship('Action', back_populates='admin')

    def serialize(self):
        return {
            'admin_id': self.id,
            'email': self.email,
            'isDeleted': self.isDeleted
        }

class Feedback(Base):
    __tablename__ = 'feedback'
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    email = Column(String(100))
    text = Column(Text, nullable=False)
    submission_date = Column(DateTime(timezone=True), default=func.now())
    isDeleted = Column(Integer, default=False, nullable=False)
    actions = relationship('Action', back_populates='feedback')

    def serialize(self):
        return {
            'feedback_id': self.id,
            'name': self.name,
            'email': self.email,
            'text': self.text,
            'submission_date': self.submission_date,
            'isDeleted': self.isDeleted
        }

class Action(Base):
    __tablename__ = 'action'
    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey('admin.id'), nullable=False)
    feedback_id = Column(Integer, ForeignKey('feedback.id'), nullable=False)
    comment = Column(Text, nullable=False)
    action_date = Column(DateTime(timezone=True), default=func.now())

    admin = relationship('Admin', back_populates='actions')
    feedback = relationship('Feedback', back_populates='actions')

    def serialize(self):
        return {
            'action_id': self.id,
            'admin_id': self.admin_id,
            'feedback_id': self.feedback_id,
            'comment': self.comment,
            'action_date': self.action_date
        }


class MySQLDataService:

    def __init__(self):
        self.engine = create_engine('sqlite:///instance/sitemgmt.db')
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)

    def publish_to_sns(self, message: str):
        topic_arn = 'arn:aws:sns:us-east-2:073127164341:delete_admin'
        sns = boto3.client('sns', region_name='us-east-2')  

        response = sns.publish(
            TopicArn=topic_arn,
            Message=message
        )

        return response

    def reset_database(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)

    # Admin Resources

    def check_email(self, email):
        if email is None:
            return "Email cannot be null", 400

        email = email.lower()
        session = self.Session()
        admin = session.query(Admin).filter(func.lower(Admin.email) == email).first()
        session.close()

        if not admin:
            return "Email not found", 404
        if admin.isDeleted == True:
            return "Admin not activated", 400
        
        return admin.serialize()


    def get_all_admin(self):
        session = self.Session()
        admin_list = session.query(Admin).all()
        session.close()
        return jsonify([admin.serialize() for admin in admin_list])


    def get_admin(self, admin_id):
        session = self.Session()
        admin = session.query(Admin).get(admin_id)

        if not admin:
            session.close()
            return "Admin not found", 404
        if admin.isDeleted == True:
            session.close()
            return "Admin not activated", 400
        
        result = admin.serialize()
        session.close()
        return jsonify(result)


    def add_admin(self, email):
        session = self.Session()
        
        if email is None:
            session.close()
            return "Email cannot be null", 400

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            session.close()
            return "Invalid email format", 400
        else:
            email = email.lower()

        admin = session.query(Admin).filter(func.lower(Admin.email) == email).first()
        
        if not admin:
            new_admin = Admin(email=email)
            session.add(new_admin)
            session.commit()
            session.close()
            return "Successfully added an admin", 200
        else:
            if admin.isDeleted == True:
                admin.isDeleted = False
                session.commit()
                session.close()
                return "Successfully reactivated a deleted admin", 200
            else:
                session.close()
                return "admin already exists and is activated", 200


    def delete_admin(self, email):
        session = self.Session()
        admin = session.query(Admin).filter(func.lower(Admin.email) == email).first()

        if admin:
            admin.isDeleted = True
            try:
                session.commit()
                try:
                    self.publish_to_sns(f'Admin {admin.email} has been deleted')
                except (NoCredentialsError, ClientError) as e:
                    print(f"An error occurred while publishing to SNS: {e}")
                session.close()
                return "Successfully deactivated an admin", 200
            except (IntegrityError, SQLAlchemyError):
                session.rollback()
                session.close()
                return "Error deactivating an admin", 501
        else:
            session.close()
            return "Admin not found", 404


    def update_admin(self, email, new_email):
        session = self.Session()
        admin = session.query(Admin).filter(func.lower(Admin.email) == email).first()

        if admin:
            if not new_email:
                if admin.isDeleted == True:
                    admin.isDeleted = False
                    session.commit()
                    session.close()
                    return "Successfully reactivated a deleted admin", 200
                else:
                    session.close()
                    return "Email cannot be null", 400

            if not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
                session.close()
                return "Invalid email format", 400
            else:
                new_email = new_email.lower()

            if session.query(Admin).filter(func.lower(Admin.email) == new_email).first():
                session.close()
                return "Email already exists", 400

            admin.email = new_email

            if admin.isDeleted == True:
                admin.isDeleted = False
                session.commit()
                session.close()
                return "Successfully activated an admin and updated the email", 200
            else:
                session.commit()
                session.close()
                return "Successfully updated an admin email", 200

        else:
            session.close()
            return "Admin not found", 404

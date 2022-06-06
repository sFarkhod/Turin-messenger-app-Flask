
# from flask_sqlalchemy import SQLAlchemy
# import sqlalchemy

# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////database.db'
# db = sqlalchemy(app)

# class User(db.Model):
#     __tablename__ = 'User'
#     id = db.Column(db.Integer, primary_key=True)
#     email = db.Column(db.String(100), nullable=False, unique=True)
#     name = db.Column(db.String(), nullable=False)

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bla-bla-bla'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
"""to skip FSA Deprecation Warning"""
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////database.db'
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'User'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    name = db.Column(db.String(), nullable=False)

# app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True


db = SQLAlchemy(app)
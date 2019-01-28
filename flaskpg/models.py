from datetime import datetime
from flaskpg import db, login_manager
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), unique=True, nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)  
    password = db.Column(db.String(60), unique=True, nullable=False)
    phone = db.Column(db.Integer, nullable=True)
    user_role = db.Column(db.String(20), nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    pgs = db.relationship('PGInfo', backref='owner', lazy=True)
    bookedpgs = db.relationship('PGBooked', backref='customer', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"


class PGInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pg_name = db.Column(db.String(200), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    location_info = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    pg = db.relationship('PGBooked', backref='pg', lazy=True)


    def __repr__(self):
        return f"PGInfo('{self.pg_name}', '{self.date_posted}', '{self.location_info}', '{self.price}', '{self.image_file}')"

class PGBooked(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    pg_id = db.Column(db.Integer, db.ForeignKey(PGInfo.id))
    name = db.Column(db.String(200), nullable=False)
    location_info =  db.Column(db.String(200), nullable=False)
    owner = db.Column(db.String(200), nullable=False)
    phone =  db.Column(db.Integer)

    def __repr__(self):
        return f"PGBooked('{self.name}')"
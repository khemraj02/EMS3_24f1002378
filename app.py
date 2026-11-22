from flask import Flask
from src.models import db,Role,User
from flask_security import SQLAlchemyUserDatastore, Security
from werkzeug.security import generate_password_hash


app = Flask(__name__)

app.debug=True
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///examination-portal4.sqlite3'
app.config["SECRET_KEY"] = "wybrewru-bnrlne-bnrlntg-rnwl"
app.config["SECURITY_PASSWORD_SALT"] = "dfg56687utyrger34r45"
db.init_app(app)
app.app_context().push()

datastore = SQLAlchemyUserDatastore(db,User,Role)
app.security = Security(app, datastore)

from src.contoller import *

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not app.security.datastore.find_role("admin"):
            admin_role = app.security.datastore.create_role(name="admin")
            app.security.datastore.create_role(name="student")
            app.security.datastore.create_role(name="examiner")
            
            admin = app.security.datastore.create_user(username="Admin", email="admin@gmail.com", 
                                                       password=generate_password_hash("123"))
            admin.roles.append(admin_role)
            db.session.commit()
    app.run()
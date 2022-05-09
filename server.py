#from attr import validate
from flask import Flask, url_for, redirect, render_template, request
from sqlalchemy.orm.exc import FlushError 
import pandas as pd
import sqlite3
from flask_migrate import Migrate
from flask_settings import BasicConfig
import os, pytesseract
from flask_uploads import UploadSet, configure_uploads, IMAGES
from PIL import Image
import cv2
from imutils import contours
import pyodbc  
import urllib
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_wtf import FlaskForm 
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError, DataRequired, Email, EqualTo
from flask_bcrypt import Bcrypt
from sqlalchemy import create_engine
SERVER = 'sony'
DATABASE = 'abdul_base'
DRIVER = 'SQL Server'
USERNAME = 'sa'
PASSWORD = 'Tunslaw17!'
DATABASE_CONNECTION = f'mssql://{USERNAME}:{PASSWORD}@{SERVER}/{DATABASE}?driver={DRIVER}'

engine = create_engine(DATABASE_CONNECTION)
connection = engine.connect()
import pandas as pd
import numpy as np
import pathlib
import pyodbc
def read_query_sql(script):
    conn = pyodbc.connect('Driver={SQL Server};'
                        'Server=sony;'
                        'Database=abdul_base;'
                        'UID=sa;'
                        'PWD=Tunslaw17!'
                          )
    dfs = pd.read_sql_query(script, conn, index_col=None,parse_dates=None)
    conn.close()
    return dfs

# Path for current location
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\SONY-VIAO\.jupyter\tesseract.exe'
project_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__,
            static_url_path = '',
            static_folder = 'static',
            template_folder = 'templates')

photos = UploadSet('photos', IMAGES)
bcrypt=Bcrypt(app)
db =SQLAlchemy(app)
migrate = Migrate(app, db)
app.config['DEBUG'] = False
SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY
#app.secret_key = settings.SECRET_KEY
app.config['UPLOAD_FOLDER'] = 'images'
params = urllib.parse.quote_plus('DRIVER={SQL Server};SERVER=sony;DATABASE=abdul_base;UID=sa;PWD=Tunslaw17!;')
app.config['SQLALCHEMY_DATABASE_URI'] = "mssql+pyodbc:///?odbc_connect=%s" % params
#connection = pyodbc.connect('Driver={SQL Server};Server=.;Database=abdul_base;uid=sa;pwd=Tunslaw17!')
#app.config["SQLALCHEMY_DATABASE_URI"] = "mssql+pyodbc://<sa>:<Tunslaw17!>/MyTestDb?driver=SQL+Server?trusted_connection=yes"
#app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

class Users(db.Model,UserMixin):
    id=db.Column(db.String(20),nullable=False)
    username=db.Column(db.String(20),nullable=False, primary_key=True)
    password=db.Column(db.String(80),nullable=False)
class RegisterForm(FlaskForm):
     id = StringField(validators=[InputRequired(), Length(min =4, max =20)], render_kw={'placeholder':'id'})
     username = StringField(validators=[InputRequired(), Length(min =4, max =20)], render_kw={'placeholder':'Username'})

     password = PasswordField("Password", validators=[InputRequired(), Length(min =4, max =20)], render_kw={'placeholder':'password'})
     #confirm_password = PasswordField("Confirm Password")

     #first_name = StringField("First Name", validators=[DataRequired()])
     #last_name = StringField("Last Name", validators=[DataRequired()])
     def validate_username(self,username):
         existing_user_username=Users.query.filter_by(username=username.data).first()

         if existing_user_username:
             raise ValidationError('That username already exists. Please choose a different one.')

     submit = SubmitField("Register")
     
class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min =4, max =20)], render_kw={'placeholder':'Username'})

    password = PasswordField("Password", validators=[InputRequired(), Length(min =4, max =20)], render_kw={'placeholder':'password'})
     

    submit = SubmitField("Login")
# Class for Image to Text
class GetText(object):
    
    def __init__(self, file):
        image = cv2.imread((project_dir + '/images/' + file))
        height, width, _ = image.shape
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5,5), 0)
        thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        cnts = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]
        cnts, _ = contours.sort_contours(cnts, method="left-to-right")

        plate = ""
        for c in cnts:
            area = cv2.contourArea(c)
            x,y,w,h = cv2.boundingRect(c)
            center_y = y + h/2
            if area > 3000 and (w > h) and center_y > height/2:
                ROI = image[y:y+h, x:x+w]
                data = pytesseract.image_to_string(ROI, lang='eng', config='--psm 6')
                plate += data
        self.file = plate
        #self.file = pytesseract.image_to_string(cv2.imread(project_dir + '/images/' + file))


# Home page
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # Check if the form is empty
        if 'photo' not in request.files:
            return 'there is no photo in form'
           
        photo = request.files['photo']
        path = os.path.join(app.config['UPLOAD_FOLDER'], photo.filename)
        # Save the photo in the upload folder
        photo.save(path)
        
        # Class instance 
        textObject = GetText(photo.filename)
        result = textObject.file
        result =result.replace(" ",'')
        my_dict={}
        my_dict[photo.filename]=result
        df1 = pd.DataFrame(my_dict.items())
        df1.to_sql(name='plate_number',con= engine,index =False,if_exists ='append')
        table=read_query_sql('select * from Users')
        if result in list(table.id.str.replace(" ",'')):
            out="Found in DB"
            return redirect(url_for('result', result=result+' and '+out))
        else:
            inn="Not Found in DB"
            return redirect(url_for('result', result=result+' and '+inn))
        # Send the result text as a session to the /result route
       
        
    return render_template('index.html')

# Result page
@app.route('/result', methods=['GET', 'POST'])
def result():
    result = request.args.get('result', None)
    return render_template('result.html', result=result)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form=RegisterForm()
    #result = request.args.get('result', None)
    if form.validate_on_submit():
        hashed_password=bcrypt.generate_password_hash(form.password.data)
        new_user=Users(id=form.id.data,username=form.username.data, password=hashed_password)
        #new_id=Users(id=form.id.data)
        try:

            db.session.add(new_user)
            #db.session.add(new_id)
            db.session.commit()
        except FlushError:
            result = request.args.get('result', None)
            db.session.rollback()
        #return redirect(url_for('login'))
        return render_template('index.html')
    return render_template('register.html',form=form)
    #return render_template('index.html')
@app.route('/login', methods=['GET', 'POST'])
def login():
    form=LoginForm()
    #result = request.args.get('result', None)
    return render_template('login.html', form=form)
    return redirect('index.html')
if __name__ == '__main__':
    app.run(host='0.0.0.0')
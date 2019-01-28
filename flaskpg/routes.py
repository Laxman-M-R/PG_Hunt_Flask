import secrets, os, csv
from elasticsearch import Elasticsearch
from celery import Celery
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort, jsonify
from flaskpg import app, db, bcrypt
from flaskpg.forms import RegistrationForm, LoginForm, UpdateAccountForm, PGInfoForm
from flaskpg.models import User, PGInfo, PGBooked
from flask_login import login_user, current_user, logout_user, login_required

es = Elasticsearch()

app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

@app.route("/")
@app.route("/home")
def home():
    pgs = PGInfo.query.all()
    return render_template('home.html', pgs=pgs)

@app.route("/about")
def about():
    return render_template('about.html', title='About')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    # user_roles = ['Owner', 'Customer']
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password, user_role=form.user_role.data)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.username.data}!', 'success')
        return redirect(url_for('home'))
    return render_template('register.html', title='Register', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = randomhex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    # bookedpgs = PGBooked.query.get_or_404(pg_id)
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)         
    return render_template('account.html', title='Account', image_file=image_file, form=form)


def save_pg_picture():
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = randomhex + f_ext
    picture_path = os.path.join(app.root_path, 'static/pg_pics', picture_fn)

    output_size = (200, 250)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

@app.route("/pg/new", methods=['GET', 'POST'])
@login_required
def postpg():
    form = PGInfoForm()
    if form.validate_on_submit():
        # if form.picture.data:
        #     picture_file = save_pg_picture(form.picture.data)            
        pg = PGInfo(pg_name=form.pg_name.data, location_info=form.location.data, body=form.pg_details.data, price=form.price.data, owner=current_user)
        db.session.add(pg)
        db.session.commit()
        # body = {
        #     'id': db_index[i].id,
        #     'pg_name': db_index[i].pg_name,
        #     'price':db_index[i].price,
        #     'location_info':db_index[i].location_info
        # }
        # body_index.append(body)
        # es.index(index='cons',doc_type='title', id=id_, body=body)
        pgs = db.session.query(PGInfo).all()
        pgsdict = pgs
        flash("Your pginfo has been updated", 'success')
        return redirect(url_for('home', pgsdict=pgsdict))
    # image_file = url_for('static', filename='pg_pics/' + picture_file)
    return render_template('pginfo.html', title='PGInfo', form=form, legend='New PG')


@app.route("/pg/<int:pg_id>", methods=['GET', 'POST'])
def pg(pg_id):
    pg = PGInfo.query.get_or_404(pg_id)
    return render_template('pg.html', title=pg.pg_name, pg=pg)

@app.route("/pg/<int:pg_id>/update", methods=['GET', 'POST'])
def update_pg(pg_id):
    pg = PGInfo.query.get_or_404(pg_id)
    if pg.owner != current_user:
        abort(403)
    form = PGInfoForm()
    if form.validate_on_submit():
        pg.pg_name = form.pg_name.data
        pg.body = form.pg_details.data
        pg.location_info = form.location.data
        pg.price = form.price.data
        db.session.commit()
        flash("Your pg details are updated!", 'success')
        return redirect(url_for('pg', pg_id=pg.id))
    elif request.method == 'GET':
        form.pg_name.data = pg.pg_name
        form.pg_details.data = pg.body
        form.location.data = pg.location_info
        form.price.data = pg.price
    return render_template('pginfo.html', title='Update PG', form=form, legend='Update PG')


@app.route("/pg/<int:pg_id>/delete", methods=['POST'])
@login_required
def delete_pg(pg_id):
    pg = PGInfo.query.get_or_404(pg_id)
    if pg.owner != current_user:
        abort(403)
    db.session.delete(pg)
    db.session.commit()
    flash('Your pg has been deleted!', 'success')
    return redirect(url_for('home'))


@app.route("/pg/<int:pg_id>/book_pg", methods=['GET','POST'])
@login_required
def book_pg(pg_id):
    if current_user.is_authenticated:    
        pg = PGInfo.query.get_or_404(pg_id)   
        bookedpg = PGBooked(customer=current_user, name=pg.pg_name, location_info=pg.location_info, owner=pg.owner.username, phone=pg.owner.phone)        
        db.session.add(bookedpg)
        db.session.commit()        
        # db.session.delete(pg)
        # db.session.commit()
        flash("You have booked the pg!", 'success')
        return redirect(url_for('display_booked_pgs'))


@app.route("/booked_pgs", methods=['GET', 'POST'])
@login_required
def display_booked_pgs():
    bookedpgs = PGBooked.query.filter_by(customer_id=current_user.id).all()       
    return render_template('bookedpg.html', title='Booked PGs', bookedpgs=bookedpgs)



@app.route('/insert-data')
def insert_data():
    INDEX_NAME = 'cons'
    # if not es.indices.exists(INDEX_NAME):
    es.indices.create('cons')        
    db_index = PGInfo.query.all()
    body_index = []
    id_ = 1
    for i in range(len(db_index)):
        body = {
            'id': db_index[i].id,
            'pg_name': db_index[i].pg_name,
            'price':db_index[i].price,
            'location_info':db_index[i].location_info
        }
        body_index.append(body)
        es.index(index='cons',doc_type='title', id=id_, body=body)
        id_ += 1
    return jsonify(body_index)

@app.route('/search', methods=['GET','POST'])
@login_required
def search():
  if request.method == 'POST':
      keyword = request.form['keyword']
      search_query = {
          "query": {
              "multi_match": {
                  "query": keyword+"*",
                  "fields": ["pg_name", "location_info"]
              }
          }
      }
      es.indices.refresh(index='cons')
      resp = es.search(index='cons', doc_type='title', body=search_query)
      return render_template('search.html',keyword=keyword,response=resp)
  return render_template('layout.html', response=resp)


@celery.task
def download_data():
   with app.app_context():
       pg_info = PGInfo.query.all()
       all_pg = []
       for pg in pg_info:
           pg_data = []
           pg_data.append(pg.pg_name)
           pg_data.append(pg.location_info)
           pg_data.append(pg.price)
           pg_data.append(pg.body)
           all_pg.append(pg_data)        
           filepath = '/home/laxman/projects/python/Flask/Flask_PG/user_data.csv'
       with open(filepath,'w') as output_file:
           pg_info_writer = csv.writer(output_file)
           for row in all_pg:
               pg_info_writer.writerow(row)        
               return {'current':100,'status':'Task completed', 'filepath':filepath}

@app.route('/download',methods=['GET','POST'])
def download():
   task = download_data.apply_async()
   return jsonify({}),202, {'Location': url_for('downloadstatus',task_id=task.id)}

@app.route('/status/<task_id>')
def downloadstatus(task_id):
   task = download_data.AsyncResult(task_id)
   if task.state == 'PENDING':
       response = {
           'state': task.state,
           'current': 0,
           'status': 'Pending...'
       }
   elif task.state != 'FAILURE':
       response = {
           'state': task.state,
           'current': task.info.get('current', 0),
           'status': task.info.get('status', '')
       }
       if 'filepath' in task.info:
           response['filepath'] = task.info['filepath']
   else:
       response = {
           'state': task.state,
           'current': 1,
           'status': str(task.info),
       }
   return jsonify(response)

# @app.route("/booked_pgs/delete", methods=['POST'])
# @login_required
# def delete_booked_pg():
#     delete_booked_pg = PGBooked.query.get_or_404(pg_id=PGInfo.id)
#     if delete_booked_pg.customer != current_user:
#         abort(403)    
#     db.session.delete(delete_booked_pg)
#     db.session.commit()
#     flash('Your booked pg has been deleted!', 'success')
#     return redirect(url_for('home'))
    




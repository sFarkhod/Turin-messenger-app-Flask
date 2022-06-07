import os
import secrets
from PIL import Image
from flask import config, render_template, sessions, url_for, flash, redirect, request, abort, session
from flask_wtf import file
from elturino import app, db, bcrypt, mail, socketio
from flask_socketio import join_room
from datetime import datetime
from elturino.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm, RequestResetForm, ResetPasswordForm
from elturino.models import User, Post, Messages
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from itsdangerous import URLSafeSerializer, SignatureExpired, BadSignature



s = URLSafeSerializer(app.config['SECRET_KEY'])


# /////////////////////////////////////////////////////////////// #

@app.route("/")
@app.route("/homepage")
def homepage():
    return render_template('home_page.html')


# /////////////////////////////////////////////////////////////// #

@app.route("/home")
@login_required
def home():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template('home.html', posts=posts)


# /////////////////////////////////////////////////////////////// #

@app.route("/about")
def about():
    return render_template('about.html', title='About')


# /////////////////////////////////////////////////////////////// #

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hash_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hash_password)
        db.session.add(user)
        db.session.commit()

        email = request.form['email']
        token = s.dumps(email, salt='email-confirm')

        msg = Message('Confirm Email', sender='noreply@demo.com', recipients=[email])

        link = url_for('confirm_email', token=token, _external=True)

        msg.body = 'Your link is {}'.format(link)

        mail.send(msg)

        return '<h1>We gonna send emai to {}. Please check your email</h1>'.format(email, token)
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)




# ///////////////////////////////// Forms for confirmation link to email

# @app.route("/confirm", methods=['GET', 'POST'])
# def confirm():
#     if request.method == 'GET':
#         return redirect(url_for('login'))

#     email = request.form['email']
#     token = s.dumps(email, salt='email-confirm')

#     msg = Message('Confirm Email', sender='noreply@demo.com', recipients=[email])

#     link = url_for('confirm_email', token=token, _external=True)

#     msg.body = 'Your link is {}'.format(link)

#     mail.send(msg)

#     return '<h1>The email is you entered is {}. The token is you used {}</h1>'.format(email, token)




# /////////////////////////////////////////////////////////////// #

@app.route('/confirm_email/<token>')
def confirm_email(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=180)
    except SignatureExpired:
        return '<h1>The token is expired!!</h1>'
    except BadSignature:
        return '<h1>This is token is not match</h1>'
    return redirect(url_for('login'))



# /////////////////////////////////////////////////////////////// #

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
            flash('Login Unsuccessful. Please check your email and password one more time', 'danger')
    return render_template('login.html', title='Login', form=form)


# /////////////////////////////////////////////////////////////// #

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


# /////////////////////////////////////////////////////////////// #

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

# /////////////////////////////////////////////////////////////// #



def save_image(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/post_pics', picture_fn)


    form_picture.save(picture_path)

    return picture_fn


# /////////////////////////////////////////////////////////////// #

@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Account has been updated!!. Enjoy now!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form)


# /////////////////////////////////////////////////////////////// #

@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, image=save_image(form.image.data), author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Post has been created!!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Post',
                           form=form, legend='New Post')


# /////////////////////////////////////////////////////////////// #

@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, post=post)


# /////////////////////////////////////////////////////////////// #

@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Post has been updated!!. Enjoy now', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Update Post',
                           form=form, legend='Update Post')


# /////////////////////////////////////////////////////////////// #

@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been successfuly deleted!!. ', 'success')
    return redirect(url_for('home'))


# /////////////////////////////////////////////////////////////// #

@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user)\
        .order_by(Post.date_posted.desc())\
        .paginate(page=page, per_page=5)
    return render_template('user_posts.html', posts=posts, user=user)



# /////////////////////////////////////////////////////////////// #

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='noreply@demo.com',
                  recipients=[user.email])
    msg.body = f'''To reset your password please visit to the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request or there has some problem then simply ignore this email. Thank you for your attention!
'''
    mail.send(msg)

# /////////////////////////////////////////////////////////////// #

@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An instructions to reset your password is sent to your email. Please check your email!', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


# /////////////////////////////////////////////////////////////// #

@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('This is an invalid or expired token. Sorry!', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been successfuly updated!! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)

# /////////////////////////////////////////////////////////////////////////////////

@app.route('/message')
@login_required
def message():
    data1 = Messages.query.filter_by(to=current_user.username).all()
    data2 = Messages.query.filter_by(by=current_user.username).all()
    data = []

    for da in data1:
        data.append(da.by)
    for da in data2:
        data.append(da.to)
    data = list(dict.fromkeys(data))

    return render_template('message.html', people=data)

# /////////////////////////////////////////////////////////////// #

@app.route('/message/to=<string:to>')
@login_required
def message_to(to):
    if current_user.is_authenticated:
        exists = User.query.filter_by(username=to).first()
        if exists:
            l1 = Messages.query.filter_by(to=current_user.username).all()
            l2 = Messages.query.filter_by(by=current_user.username).all()
            d = []
            for da in l1:
                d.append(da.by)
            for da in l2:
                d.append(da.to)
            d = list(dict.fromkeys(d))

            data1 = Messages.query.filter_by(room=f'{to}-{current_user.username}').all()
            data2 = Messages.query.filter_by(room=f'{current_user.username}-{to}').all()
            data = []
            for da in data1:
                data.append(da)
            for da in data2:
                data.append(da)
            data.sort(key = lambda d:d.id)
            return render_template('message-to.html', to=to, data=data, uname=current_user.username, people=d)
    return redirect(url_for('message'))

# /////////////////////////////////////////////////////////////// #


@socketio.on('join_room')
def handle_join_room_event(data):
    room = data['room']
    data = room.split('-')
    room2 = f'{data[1]}-{data[0]}'
    join_room(room)
    join_room(room2)
    print('Users joined')


@socketio.on('send_message')
def handle_send_message(data):
    room = data['room']
    d = room.split('-')
    room2 = f'{d[1]}-{d[0]}'
    time = data['time']
    time_obj = datetime.strptime(time, '%d-%m-%Y@%H:%M')
    message_data = Messages(room=room, to=d[0], by=d[1], message=data['message'], time=time_obj)
    db.session.add(message_data)
    db.session.commit()
    socketio.emit('receive_message', data, room=(room, room2))

# /////////////////////////////////////////////////////////////// #
@app.route("/weather_api")
def weather_api():
    return render_template('weather_api.html', title='weather')


# /////////////////////////////////////////////////////////////// #

@app.route("/movie_api")
def movie_api():
    return render_template('movie_api.html', title='Movie')


# /////////////////////////////////////////////////////////////// #

@app.route('/logout_admin')
def logout_admin():
    session.clear()
    return redirect("/")


# /////////////////////////////////////////////////////////////// #

@app.route('/login_admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        if request.form.get('username') == 'sFarkhod' and request.form.get('password') == 'sFarkhod0435':
            session['logged_in'] = True
            return redirect('/admin')
        else:
            return render_template('login_admin.html', failed=True)
    return render_template('login_admin.html')






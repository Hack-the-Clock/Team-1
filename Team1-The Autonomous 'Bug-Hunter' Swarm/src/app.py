# app.py

import os
from flask import Flask, request, render_template, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import click

# --- App Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_very_secret_key_that_will_be_changed'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- Database Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    # Roles: 'USER' or 'ADMIN'
    role = db.Column(db.String(20), nullable=False, default='USER')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', backref=db.backref('posts', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes ---
@app.route('/')
def index():
    posts = Post.query.all()
    app.logger.info('Visited index page.')
    return f"<h1>Blog Posts</h1>" + "".join([f"<div><h2>{p.title}</h2><p>by {p.author.username}</p><p>{p.content}</p></div>" for p in posts])

@app.route('/register', methods=['GET', 'POST'])
def register():
    # A simple way to register a user via query params for this demo
    # e.g., /register?username=bob&password=pwd
    if request.args.get('username') and request.args.get('password'):
        username = request.args.get('username')
        password = request.args.get('password')
        
        if User.query.filter_by(username=username).first():
            app.logger.warn(f"Registration failed: User {username} already exists.")
            return "User already exists", 400
        
        new_user = User(username=username, role='USER')
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        app.logger.info(f"New user created: {username}")
        return redirect(url_for('login'))
    return "Use query params ?username=X&password=Y to register."

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Simple login via query params
    # e.g., /login?username=bob&password=pwd
    if request.args.get('username') and request.args.get('password'):
        username = request.args.get('username')
        password = request.args.get('password')
        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            app.logger.warn(f"Failed login attempt for user: {username}")
            return 'Invalid username or password', 401
        
        login_user(user)
        app.logger.info(f"User {username} logged in successfully.")
        return redirect(url_for('index'))
    return "Use query params ?username=X&password=Y to login."

@app.route('/logout')
@login_required
def logout():
    app.logger.info(f"User {current_user.username} logged out.")
    logout_user()
    return redirect(url_for('index'))

@app.route('/create_post', methods=['GET'])
@login_required
def create_post():
    # Simple post creation via query params
    # e.g., /create_post?title=MyPost&content=MyContent
    title = request.args.get('title')
    content = request.args.get('content')
    if title and content:
        post = Post(title=title, content=content, author=current_user)
        db.session.add(post)
        db.session.commit()
        app.logger.info(f"User {current_user.username} created new post: {title}")
        return redirect(url_for('index'))
    return "Use query params ?title=X&content=Y to create post."

# --- !!! THE VULNERABLE ROUTE !!! ---
@app.route('/admin/delete/<int:post_id>', methods=['GET'])
@login_required # <-- PROBLEM: This checks for LOGIN, but not for ADMIN role!
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # CRITICAL LOGIC FLAW IS HERE
    # A regular 'USER' can access this route and delete anyone's post.
    # This is the "logic breach" our Log-Watcher will be built to detect.
    
    db.session.delete(post)
    db.session.commit()
    
    # This log line is the "smoking gun" our Log-Watcher will find
    app.logger.critical(f"ADMIN ACTION: User {current_user.username} (role: {current_user.role}) deleted post {post_id}.")
    return f"Post {post_id} deleted by {current_user.username}."
# --- !!! END VULNERABLE ROUTE !!! ---
# --- CLI Commands to set up the DB ---
@app.cli.command('init-db')
def init_db_command():
    """Drops and creates all database tables."""
    db.drop_all()
    db.create_all()
    print('Initialized the database.')

@app.cli.command('create-admin')
@click.argument('username')
@click.argument('password')
def create_admin_command(username, password):
    """Creates a new admin user."""
    if User.query.filter_by(username=username).first():
        print(f"Error: User {username} already exists.")
        return
        
    admin_user = User(username=username, role='ADMIN')
    admin_user.set_password(password)
    db.session.add(admin_user)
    db.session.commit()
    print(f"Admin user {username} created.")

if __name__ == '__main__':
    # This is only for local dev, not for production container
    app.run(debug=True)
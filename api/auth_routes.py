import re

from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from flask_jwt_extended import jwt_required

from services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__)

def init_auth_routes(app, auth_service: AuthService):
    @auth_bp.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')

            if not email or not password:
                flash("Відсутня ел. пошта та/або пароль.", "danger")
                return render_template('register.html')

            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                flash("Невірний формат ел. пошти.", "danger")
                return render_template('register.html')

            if len(password) < 8:
                flash("Пароль має містити не менше 8 символів.", "danger")
                return render_template('register.html')
            if not re.search(r"[0-9]", password):
                flash("Пароль має містити хоча б одну цифру.", "danger")
                return render_template('register.html')
            if not re.search(r"[A-Z]", password):
                flash("Пароль має містити хоча б одну велику літеру.", "danger")
                return render_template('register.html')

            try:
                user = auth_service.register_user(email, password)
                flash("Реєстрація успішна", "success")
                return redirect(url_for('auth.login'))
            except ValueError as e:
                flash(f"Сталася помилка:\n{e}", "danger")
                return render_template('register.html')
        return render_template('register.html')

    @auth_bp.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')

            if not email or not password:
                flash("Некоректні дані для входу", "danger")
                return render_template('login.html')

            response = auth_service.login(email, password)
            if response:
                user = auth_service.user_repository.get_by_email(email)
                session['user_id'] = user.id
                flash("Вхід успішний", "success")
                return response
            else:
                flash("Некоректні дані для входу", "danger")
                return render_template('login.html')
        return render_template('login.html')

    @auth_bp.route('/logout')
    @jwt_required()
    def logout():
        response = redirect(url_for('index'))
        auth_service.logout(response)
        flash("Ви вийшли", "success")
        return response

    app.register_blueprint(auth_bp, url_prefix='/auth')
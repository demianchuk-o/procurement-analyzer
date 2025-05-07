from typing import Tuple, Optional

from flask import Flask, Response, redirect, url_for
from flask_jwt_extended import (
    JWTManager, create_access_token, unset_jwt_cookies, set_access_cookies
)

from models import User
from repositories.user_repository import UserRepository
from services.password_service import PasswordService


class AuthService:
    def __init__(self, app: Flask, user_repository: UserRepository,
                 password_service: PasswordService):
        self.app = app
        app.config['JWT_TOKEN_LOCATION'] = ['cookies']
        app.config['JWT_COOKIE_CSRF_PROTECT'] = False
        self.jwt = JWTManager(app)
        self.user_repository = user_repository
        self.password_service = password_service

    def register_user(self, email: str, password: str) -> User:
        """Registers a new user, hashing the email and setting the password."""

        existing_user = self.user_repository.get_by_email(email)
        if existing_user:
            raise ValueError("User with this email already exists")

        user = User(email=email)
        user.password_hash = password
        self.user_repository.add(user)
        self.user_repository.commit()
        return user

    def login(self, email: str, password: str) -> Optional[Response]:
        user = self.user_repository.get_by_email(email)
        if not user or not self.password_service.check_password(user.password_hash, password):
            return None

        access_token = create_access_token(identity=str(user.id))
        response = redirect(url_for('index'))
        set_access_cookies(response, access_token)
        return response

    def logout(self, resp: Response) -> None:
        unset_jwt_cookies(resp)
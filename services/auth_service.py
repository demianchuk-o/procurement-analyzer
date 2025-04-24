from typing import Tuple, Optional

from flask import Flask, jsonify
from flask_jwt_extended import (
    JWTManager, create_access_token, unset_jwt_cookies
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
        self.user_repo = user_repository
        self.password_service = password_service


    def login(self, email: str, password: str) -> Optional[Tuple[str, User]]:
        email_hash = self.user_repo.hash_email(email)
        user = self.user_repo.get_by_email(email_hash)
        if not user or not self.password_service.check_password(user.password_hash, password):
            return None
        access_token = create_access_token(identity=email)
        return access_token, user

    def logout(self):
        resp = jsonify({'logout': True})
        unset_jwt_cookies(resp)
        return resp

    def authenticate(self, email: str) -> Optional[User]:
        email_hash = self.user_repo.hash_email(email)
        user = self.user_repo.get_by_email(email_hash)
        return user
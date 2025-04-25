from werkzeug.security import check_password_hash


class PasswordService:
    def check_password(self, password_hash: str, password: str) -> bool:
        """Check if the provided password matches the stored password hash."""
        return check_password_hash(password_hash, password)
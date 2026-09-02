"""Repository for users and roles."""

from werkzeug.security import check_password_hash, generate_password_hash

from ..domain.users import ROLE_CLASSES, build_user
from ..exceptions import AuthenticationError, NotFoundError, ValidationError
from ..utils import require_choice, require_text
from .base import BaseRepository

USER_SELECT = """
    SELECT u.id, u.username, u.full_name, u.email, u.department, u.phone,
           u.is_active, u.created_at, r.name AS role
    FROM users u JOIN roles r ON r.id = u.role_id
"""


class UserRepository(BaseRepository):
    """Loads and stores `User` aggregates, rebuilding the concrete subclass."""

    table = "users"

    # ------------------------------------------------------------- mapping
    @staticmethod
    def to_domain(row):
        if row is None:
            return None
        return build_user(
            row["role"],
            user_id=row["id"],
            username=row["username"],
            full_name=row["full_name"],
            email=row["email"],
            department=row["department"],
            phone=row["phone"],
            is_active=bool(row["is_active"]),
        )

    # --------------------------------------------------------------- roles
    def role_id(self, role_name):
        row = self.query_one("SELECT id FROM roles WHERE name = ?", (role_name,))
        if row is None:
            raise NotFoundError("Unknown role: %s" % role_name)
        return row["id"]

    def roles(self):
        return [dict(row) for row in self.query("SELECT * FROM roles ORDER BY id")]

    # --------------------------------------------------------------- reads
    def get(self, user_id):
        row = self.query_one(USER_SELECT + " WHERE u.id = ?", (user_id,))
        return self.to_domain(row)

    def require_user(self, user_id):
        user = self.get(user_id)
        if user is None:
            raise NotFoundError("User %s was not found." % user_id)
        return user

    def get_by_username(self, username):
        row = self.query_one(USER_SELECT + " WHERE u.username = ?", ((username or "").strip(),))
        return self.to_domain(row)

    def list_users(self, role=None, active_only=False):
        sql = USER_SELECT
        clauses = []
        params = []
        if role:
            clauses.append("r.name = ?")
            params.append(role)
        if active_only:
            clauses.append("u.is_active = 1")
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY r.id, u.full_name"
        return [self.to_domain(row) for row in self.query(sql, params)]

    def maintenance_staff(self):
        return self.list_users(role="MAINTENANCE", active_only=True)

    def role_counts(self):
        rows = self.query(
            "SELECT r.name AS role, COUNT(u.id) AS total FROM roles r "
            "LEFT JOIN users u ON u.role_id = r.id GROUP BY r.id ORDER BY r.id")
        return {row["role"]: row["total"] for row in rows}

    # -------------------------------------------------------------- writes
    def add(self, username, full_name, email, password, role, department=None,
            phone=None, is_active=True):
        username = require_text(username, "username", minimum=3, maximum=40)
        full_name = require_text(full_name, "full name", minimum=3, maximum=80)
        email = require_text(email, "email", minimum=5, maximum=120).lower()
        role = require_choice(role, "role", set(ROLE_CLASSES))
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValidationError("A valid email address is required.", {"field": "email"})
        if len(password or "") < 6:
            raise ValidationError("Password must be at least 6 characters.",
                                  {"field": "password"})
        if self.exists("username = ?", (username,)):
            raise ValidationError("Username '%s' is already taken." % username,
                                  {"field": "username"})
        if self.exists("email = ?", (email,)):
            raise ValidationError("Email '%s' is already registered." % email,
                                  {"field": "email"})
        cursor = self.execute(
            "INSERT INTO users (username, full_name, email, password_hash, role_id,"
            " department, phone, is_active) VALUES (?,?,?,?,?,?,?,?)",
            (username, full_name, email, generate_password_hash(password),
             self.role_id(role), department, phone, 1 if is_active else 0))
        return self.get(cursor.lastrowid)

    def upsert_seed_user(self, username, full_name, email, password, role,
                         department=None, phone=None):
        """Idempotent insert used by the seeding process."""
        existing = self.get_by_username(username)
        if existing is not None:
            return existing
        return self.add(username, full_name, email, password, role, department, phone)

    def change_role(self, user_id, role):
        role = require_choice(role, "role", set(ROLE_CLASSES))
        self.require_user(user_id)
        self.execute("UPDATE users SET role_id = ? WHERE id = ?",
                     (self.role_id(role), user_id))
        return self.get(user_id)

    def set_active(self, user_id, is_active):
        self.require_user(user_id)
        self.execute("UPDATE users SET is_active = ? WHERE id = ?",
                     (1 if is_active else 0, user_id))
        return self.get(user_id)

    # --------------------------------------------------------- credentials
    def authenticate(self, username, password):
        row = self.query_one(
            USER_SELECT + " WHERE u.username = ?", ((username or "").strip(),))
        if row is None:
            raise AuthenticationError("Unknown username or password.")
        stored = self.query_one("SELECT password_hash FROM users WHERE id = ?", (row["id"],))
        if not check_password_hash(stored["password_hash"], password or ""):
            raise AuthenticationError("Unknown username or password.")
        if not row["is_active"]:
            raise AuthenticationError("This account has been deactivated.")
        return self.to_domain(row)

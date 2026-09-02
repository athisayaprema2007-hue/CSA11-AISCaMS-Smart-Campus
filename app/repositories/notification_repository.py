"""Repository for user notifications."""

from ..domain.notification import Notification
from ..exceptions import NotFoundError
from .base import BaseRepository


class NotificationRepository(BaseRepository):
    table = "notifications"

    @staticmethod
    def to_domain(row):
        if row is None:
            return None
        return Notification(
            notification_id=row["id"], user_id=row["user_id"], title=row["title"],
            message=row["message"], category=row["category"],
            entity_type=row["entity_type"], entity_id=row["entity_id"],
            is_read=bool(row["is_read"]), created_at=row["created_at"])

    def get(self, notification_id):
        return self.to_domain(self.query_one(
            "SELECT * FROM notifications WHERE id = ?", (notification_id,)))

    def for_user(self, user_id, unread_only=False, limit=25):
        sql = "SELECT * FROM notifications WHERE user_id = ?"
        params = [user_id]
        if unread_only:
            sql += " AND is_read = 0"
        sql += " ORDER BY created_at DESC, id DESC LIMIT %d" % int(limit)
        return [self.to_domain(row) for row in self.query(sql, params)]

    def unread_count(self, user_id):
        return int(self.scalar(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
            (user_id,)))

    def add(self, user_id, title, message, category, entity_type=None, entity_id=None):
        cursor = self.execute(
            "INSERT INTO notifications (user_id, title, message, category, entity_type,"
            " entity_id) VALUES (?,?,?,?,?,?)",
            (user_id, title, message, category, entity_type, entity_id))
        return self.get(cursor.lastrowid)

    def add_once(self, user_id, title, message, category, entity_type=None,
                 entity_id=None):
        """Idempotent variant used while seeding demo notifications."""
        existing = self.query_one(
            "SELECT id FROM notifications WHERE user_id = ? AND title = ? AND message = ?",
            (user_id, title, message))
        if existing:
            return self.get(existing["id"])
        return self.add(user_id, title, message, category, entity_type, entity_id)

    def mark_read(self, notification_id, user_id=None):
        sql = "UPDATE notifications SET is_read = 1 WHERE id = ?"
        params = [notification_id]
        if user_id:
            sql += " AND user_id = ?"
            params.append(user_id)
        cursor = self.execute(sql, params)
        if cursor.rowcount == 0:
            raise NotFoundError("Notification %s was not found." % notification_id)
        return self.get(notification_id)

    def mark_all_read(self, user_id):
        self.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
        return self.for_user(user_id)

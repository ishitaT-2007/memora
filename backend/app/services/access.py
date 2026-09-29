from sqlalchemy.orm import Session

from app.errors import AccrueError
from app.models import AccountAccess, User


def assert_account_access(db: Session, user: User, account_id: str) -> None:
    if user.role == "admin":
        return
    access = (
        db.query(AccountAccess)
        .filter(AccountAccess.user_id == user.id, AccountAccess.account_id == account_id)
        .first()
    )
    if not access:
        raise AccrueError("ACCOUNT_FORBIDDEN", "You do not have access to this account.", 403)

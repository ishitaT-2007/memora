from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import create_token, get_current_user, verify_password
from app.db import get_db
from app.errors import AccrueError
from app.models import Account, AccountAccess, User
from app.schemas import LoginRequest, TokenResponse

router = APIRouter(tags=["auth"])


@router.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise AccrueError("INVALID_CREDENTIALS", "Email or password is incorrect.", 401)
    token = create_token(user)
    return TokenResponse(
        access_token=token,
        user={"id": user.id, "email": user.email, "name": user.name, "role": user.role},
    )


@router.get("/api/auth/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}


@router.get("/api/accounts")
def list_accounts(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    if user.role == "admin":
        accounts = db.query(Account).order_by(Account.name).all()
    else:
        ids = [row.account_id for row in db.query(AccountAccess).filter(AccountAccess.user_id == user.id).all()]
        accounts = db.query(Account).filter(Account.id.in_(ids)).order_by(Account.name).all() if ids else []
    return {
        "accounts": [
            {
                "id": row.id,
                "name": row.name,
                "arr": row.arr,
                "segment": row.segment,
                "timezone": row.timezone,
                "status": row.status,
            }
            for row in accounts
        ]
    }

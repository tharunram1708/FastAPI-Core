from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.authorization import Role
from app.db.session import managed_database_session
from app.schemas.user import UserCreate


def upgrade_database() -> None:
    config = Config(str(ROOT_DIR / "alembic.ini"))
    command.upgrade(config, "head")


def seed_admin(username: str, email: str, password: str) -> None:
    with managed_database_session() as db:
        existing = db.user_repository.get_by_email(email)
        if existing is None:
            existing = db.auth.register_user(
                UserCreate(
                    username=username,
                    email=email,
                    password=password,
                    full_name="System Administrator",
                )
            )

        existing.role = Role.ADMIN.value
        existing.is_active = True
        existing.is_verified = True
        existing.updated_at = db.enterprise.now()
        db.enterprise.create_audit_log(
            actor_id=existing.id,
            action="SEED_ADMIN_USER",
            resource_type="user",
            resource_id=str(existing.id),
            details={"username": existing.username, "email": existing.email},
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upgrade the database and optionally seed an admin user.",
    )
    parser.add_argument("--no-admin", action="store_true", help="Only run migrations.")
    parser.add_argument("--admin-username", default=os.getenv("ADMIN_USERNAME", "admin_user"))
    parser.add_argument("--admin-email", default=os.getenv("ADMIN_EMAIL", "admin@example.com"))
    parser.add_argument("--admin-password", default=os.getenv("ADMIN_PASSWORD"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    upgrade_database()

    if args.no_admin:
        print("Database upgraded. Admin seed skipped.")
        return

    if not args.admin_password:
        raise SystemExit(
            "Set ADMIN_PASSWORD or pass --admin-password to seed the admin account."
        )

    seed_admin(args.admin_username, args.admin_email, args.admin_password)
    print(f"Database upgraded. Admin account ready: {args.admin_email}")


if __name__ == "__main__":
    main()

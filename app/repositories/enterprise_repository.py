from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.enterprise import (
    AuditLog,
    Customer,
    Document,
    Employee,
    Notification,
    OrderLineItem,
    PasswordResetToken,
    Payment,
    Product,
    RecordHistory,
    Report,
    SalesOrder,
    ScheduledJob,
    UserSession,
    WebhookEvent,
    WorkTask,
)
from app.models.item import Item
from app.repositories.base import SQLAlchemyRepository


class EnterpriseRepository:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.password_resets = SQLAlchemyRepository(session, PasswordResetToken)
        self.sessions = SQLAlchemyRepository(session, UserSession)
        self.documents = SQLAlchemyRepository(session, Document)
        self.notifications = SQLAlchemyRepository(session, Notification)
        self.audit_logs = SQLAlchemyRepository(session, AuditLog)
        self.record_history = SQLAlchemyRepository(session, RecordHistory)
        self.webhook_events = SQLAlchemyRepository(session, WebhookEvent)
        self.scheduled_jobs = SQLAlchemyRepository(session, ScheduledJob)
        self.employees = SQLAlchemyRepository(session, Employee)
        self.customers = SQLAlchemyRepository(session, Customer)
        self.products = SQLAlchemyRepository(session, Product)
        self.orders = SQLAlchemyRepository(session, SalesOrder)
        self.order_line_items = SQLAlchemyRepository(session, OrderLineItem)
        self.payments = SQLAlchemyRepository(session, Payment)
        self.tasks = SQLAlchemyRepository(session, WorkTask)
        self.reports = SQLAlchemyRepository(session, Report)

    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def create_audit_log(
        self,
        *,
        actor_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        return self.audit_logs.create(
            {
                "actor_id": actor_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details or {},
                "ip_address": ip_address,
            }
        )

    def create_history(
        self,
        *,
        resource_type: str,
        resource_id: str,
        previous_data: dict[str, Any],
        changed_by_id: UUID | None,
    ) -> RecordHistory:
        version = self.session.scalar(
            select(func.count())
            .select_from(RecordHistory)
            .where(
                RecordHistory.resource_type == resource_type,
                RecordHistory.resource_id == resource_id,
            )
        ) or 0
        return self.record_history.create(
            {
                "resource_type": resource_type,
                "resource_id": resource_id,
                "version": int(version) + 1,
                "previous_data": previous_data,
                "changed_by_id": changed_by_id,
            }
        )

    def list_audit_logs(
        self,
        *,
        action: str | None = None,
        resource_type: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        filters = []
        if action:
            filters.append(AuditLog.action == action)
        if resource_type:
            filters.append(AuditLog.resource_type == resource_type)
        return self.audit_logs.list(
            filters=filters,
            order_by=(AuditLog.created_at.desc(),),
            skip=skip,
            limit=limit,
        )

    def active_user_session(self, session_id: UUID) -> UserSession | None:
        session = self.sessions.get(session_id)
        if session is None or session.revoked_at is not None:
            return None
        session.last_seen_at = self.now()
        return session

    def list_user_sessions(self, user_id: UUID) -> list[UserSession]:
        return self.sessions.list(
            filters=(UserSession.user_id == user_id,),
            order_by=(UserSession.created_at.desc(),),
            skip=0,
            limit=100,
        )

    def revoke_user_sessions(self, user_id: UUID) -> int:
        now = self.now()
        sessions = self.list_user_sessions(user_id)
        revoked = 0
        for session in sessions:
            if session.revoked_at is None:
                session.revoked_at = now
                session.updated_at = now
                revoked += 1
        self.session.flush()
        return revoked

    def create_password_reset(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        otp_hash: str,
        expires_at: datetime,
    ) -> PasswordResetToken:
        return self.password_resets.create(
            {
                "user_id": user_id,
                "token_hash": token_hash,
                "otp_hash": otp_hash,
                "expires_at": expires_at,
            }
        )

    def get_valid_password_reset(self, token_hash: str) -> PasswordResetToken | None:
        token = self.session.scalar(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        if token is None or token.used_at is not None:
            return None
        if self._as_utc(token.expires_at) <= self.now():
            return None
        return token

    def create_notification(
        self,
        *,
        user_id: UUID | None,
        title: str,
        message: str,
        category: str = "general",
        metadata: dict[str, Any] | None = None,
    ) -> Notification:
        return self.notifications.create(
            {
                "user_id": user_id,
                "title": title,
                "message": message,
                "category": category,
                "notification_metadata": metadata or {},
                "delivered_at": self.now(),
            }
        )

    def cleanup_expired_security_records(self) -> dict[str, int]:
        now = self.now()
        old_date = now - timedelta(days=30)
        expired_resets = list(
            self.session.scalars(
                select(PasswordResetToken).where(PasswordResetToken.expires_at < now)
            )
        )
        processed_webhooks = list(
            self.session.scalars(
                select(WebhookEvent).where(
                    WebhookEvent.status == "processed",
                    WebhookEvent.updated_at < old_date,
                )
            )
        )
        for row in [*expired_resets, *processed_webhooks]:
            self.session.delete(row)
        self.session.flush()
        return {
            "expired_password_resets_deleted": len(expired_resets),
            "processed_webhooks_deleted": len(processed_webhooks),
        }

    def search_items(
        self,
        *,
        q: str,
        category: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 20,
    ) -> list[Item]:
        pattern = f"%{q.casefold()}%"
        filters = [
            Item.deleted_at.is_(None),
            or_(func.lower(Item.name).like(pattern), func.lower(Item.description).like(pattern)),
        ]
        if category:
            filters.append(Item.category == category)
        sort_columns = {
            "name": Item.name,
            "category": Item.category,
            "inventory_count": Item.inventory_count,
            "created_at": Item.created_at,
        }
        sort_column = sort_columns.get(sort_by, Item.created_at)
        order = sort_column.asc() if sort_order == "asc" else sort_column.desc()
        return list(
            self.session.scalars(
                select(Item).where(*filters).order_by(order).offset(skip).limit(limit)
            )
        )

    def _as_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

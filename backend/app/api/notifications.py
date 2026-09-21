from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.core.security import get_current_user
from app.db.models import User, Role, Notification

router = APIRouter()

@router.get("")
@router.get("/")
def get_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != Role.CUSTOMER.value:
        raise HTTPException(status_code=403, detail="Unauthorized")
    notifs = db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).all()
    return notifs

@router.patch("/{notif_id}/read")
def mark_notification_read(notif_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != Role.CUSTOMER.value:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    notif = db.query(Notification).filter(Notification.id == notif_id, Notification.user_id == current_user.id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif

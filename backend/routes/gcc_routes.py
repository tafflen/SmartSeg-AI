from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Resident, User, WasteEvent, get_db
from security import require_roles

router = APIRouter(prefix="/gcc", tags=["gcc"])


@router.get("/analytics")
def analytics(db: Session = Depends(get_db), user: User = Depends(require_roles("gcc"))):
    categories = dict(db.query(WasteEvent.category, func.count(WasteEvent.id)).group_by(WasteEvent.category).all())
    total_weight = db.query(func.coalesce(func.sum(WasteEvent.weight_grams), 0)).scalar()
    # `society_id` can be added later and this response grouped by it without changing consumers.
    return {"scope": "single_society", "societies": [{"society_id": "local-default", "resident_count": db.query(Resident).count(),
            "event_count": sum(categories.values()), "total_weight_grams": total_weight, "by_category": categories}]}


@router.get("/compliance-report")
def compliance_report(db: Session = Depends(get_db), user: User = Depends(require_roles("gcc"))):
    total = db.query(WasteEvent).count()
    correct = db.query(WasteEvent).filter(WasteEvent.confidence_score >= 0.5).count()
    return {"proxy": "confidence_score >= 0.5", "total_events": total, "correctly_segregated": correct,
            "contaminated_or_uncertain": total - correct, "compliance_percent": round((correct / total * 100) if total else 0, 2)}

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models import Customer, RetentionIntervention
from ..schemas import (
    RetentionInterventionCreate,
    RetentionInterventionResponse,
    RetentionInterventionUpdate,
)
from .auth import get_current_user

router = APIRouter(prefix="/retention", tags=["Retention Interventions"])


@router.post("/interventions", response_model=RetentionInterventionResponse, status_code=status.HTTP_201_CREATED)
async def create_intervention(
    payload: RetentionInterventionCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    customer = db.query(Customer).filter(Customer.customer_id == payload.customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {payload.customer_id} not found.",
        )

    intervention = RetentionIntervention(
        customer_id=payload.customer_id,
        prediction_id=payload.prediction_id,
        offer_type=payload.offer_type,
        status=payload.status,
        notes=payload.notes,
        created_by=current_user,
    )
    db.add(intervention)
    db.commit()
    db.refresh(intervention)
    return intervention


@router.get("/interventions", response_model=List[RetentionInterventionResponse])
async def list_interventions(
    customer_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    query = db.query(RetentionIntervention)
    if customer_id:
        query = query.filter(RetentionIntervention.customer_id == customer_id)
    if status_filter:
        query = query.filter(RetentionIntervention.status == status_filter)

    return query.order_by(RetentionIntervention.created_at.desc()).limit(limit).all()


@router.patch("/interventions/{intervention_id}", response_model=RetentionInterventionResponse)
async def update_intervention(
    intervention_id: int,
    payload: RetentionInterventionUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    intervention = db.query(RetentionIntervention).filter(
        RetentionIntervention.intervention_id == intervention_id
    ).first()
    if not intervention:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Retention intervention not found.",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(intervention, field, value)

    db.commit()
    db.refresh(intervention)
    return intervention
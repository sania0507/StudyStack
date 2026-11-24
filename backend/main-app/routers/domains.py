import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import get_current_user_id
from database import get_db
from models import Domain
from schemas import DomainCreate, DomainUpdate, DomainOut


router = APIRouter(prefix="/domains", tags=["domains"])


@router.post("", response_model=DomainOut)
def create_domain(
    domain: DomainCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    new_domain = Domain(
        id=uuid.uuid4(),
        name=domain.name,
        colour="violet",
        user_id=user_id,
        repeats_daily=domain.repeats_daily,
    )

    db.add(new_domain)
    db.commit()
    db.refresh(new_domain)

    return new_domain


@router.get("", response_model=list[DomainOut])
def get_domains(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    result = db.execute(
        select(Domain).where(Domain.user_id == user_id)
    )
    return result.scalars().all()


@router.patch("/{domain_id}", response_model=DomainOut)
def update_domain(
    domain_id: uuid.UUID,
    domain: DomainUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    existing_domain = db.scalar(
        select(Domain).where(
            Domain.id == domain_id,
            Domain.user_id == user_id,
        )
    )

    if existing_domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")

    if domain.name is not None:
        existing_domain.name = domain.name

    if domain.colour is not None:
        existing_domain.colour = domain.colour

    if domain.repeats_daily is not None:
        existing_domain.repeats_daily = domain.repeats_daily

    db.commit()
    db.refresh(existing_domain)
    return existing_domain


@router.delete("/{domain_id}")
def delete_domain(
    domain_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    existing_domain = db.scalar(
        select(Domain).where(
            Domain.id == domain_id,
            Domain.user_id == user_id,
        )
    )

    if existing_domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")

    db.delete(existing_domain)
    db.commit()

    return {"message": "Domain deleted successfully"}

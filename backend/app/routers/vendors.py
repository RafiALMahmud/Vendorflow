from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import require_vendor
from app.db.session import get_db
from app.models.identity import User, Vendor
from app.schemas.vendor import VendorCreate, VendorResponse, VendorUpdate

router = APIRouter(prefix="/vendors", tags=["vendors"])
VendorUser = Annotated[User, Depends(require_vendor)]


def owned_profile_query(current_user: User):
    return select(Vendor).where(Vendor.owner_user_id == current_user.id)


def get_owned_profile(db: Session, current_user: User) -> Vendor:
    profile = db.scalar(owned_profile_query(current_user))
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor profile not found",
        )
    return profile


@router.post(
    "/me",
    response_model=VendorResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_vendor_profile(
    payload: VendorCreate,
    current_user: VendorUser,
    db: Annotated[Session, Depends(get_db)],
) -> Vendor:
    if db.scalar(owned_profile_query(current_user)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vendor profile already exists",
        )

    profile = Vendor(owner_user_id=current_user.id, **payload.model_dump())
    db.add(profile)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vendor profile already exists",
        ) from exc
    db.refresh(profile)
    return profile


@router.get("/me", response_model=VendorResponse)
def read_vendor_profile(
    current_user: VendorUser,
    db: Annotated[Session, Depends(get_db)],
) -> Vendor:
    return get_owned_profile(db, current_user)


@router.patch("/me", response_model=VendorResponse)
def update_vendor_profile(
    payload: VendorUpdate,
    current_user: VendorUser,
    db: Annotated[Session, Depends(get_db)],
) -> Vendor:
    profile = get_owned_profile(db, current_user)
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field_name, value)
    db.commit()
    db.refresh(profile)
    return profile

import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import get_current_user_id
from database import get_db
from models import VisionItem
from schemas import VisionItemCreateFromUrl, VisionItemOut, VisionItemUpdate


router = APIRouter(prefix="/vision-items", tags=["vision"])

# Same limit as the avatar: an image board is not a file host.
MAX_IMAGE_BYTES = 2 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}

# A short timeout because a slow remote site must not hold a user's request open.
FETCH_TIMEOUT_SECONDS = 8.0


def owned_item(db: Session, item_id: uuid.UUID, user_id: uuid.UUID) -> VisionItem:
    """Looks an item up scoped to its owner, or 404.

    Same reasoning as every other router: 404 for "not yours" leaks less than
    403, which would confirm the id exists.
    """
    item = db.scalar(
        select(VisionItem).where(
            VisionItem.id == item_id,
            VisionItem.user_id == user_id,
        )
    )

    if item is None:
        raise HTTPException(status_code=404, detail="Vision item not found")

    return item


@router.get("", response_model=list[VisionItemOut])
def get_vision_items(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    items = db.scalars(
        select(VisionItem)
        .where(VisionItem.user_id == user_id)
        .order_by(VisionItem.id)
    ).all()

    return items


@router.post("/upload", response_model=VisionItemOut)
async def add_vision_item_by_upload(
    file: UploadFile,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Adds a file the user picked from their own device."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Image must be a PNG, JPEG, WebP or GIF",
        )

    data = await file.read()

    if not data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="That file is empty",
        )

    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Images must be under 2 MB",
        )

    item = VisionItem(
        id=uuid.uuid4(),
        user_id=user_id,
        caption=None,
        image_mime=file.content_type,
        image_data=data,
        x=0.0,
        y=0.0,
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


@router.post("", response_model=VisionItemOut)
async def add_vision_item_from_url(
    payload: VisionItemCreateFromUrl,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Adds a pasted link by fetching it once.

    The bytes are stored rather than the URL, because Pinterest image links
    expire: a board that stored links would slowly fill with broken tiles.
    """
    try:
        async with httpx.AsyncClient(
            timeout=FETCH_TIMEOUT_SECONDS,
            follow_redirects=True,
        ) as client:
            response = await client.get(payload.image_url)
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Could not fetch that image link",
        ) from None

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="That link did not return an image",
        )

    content_type = response.headers.get("content-type", "").split(";")[0].strip()

    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="That link is not an image (PNG, JPEG, WebP or GIF)",
        )

    data = response.content

    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="That image is larger than 2 MB",
        )

    item = VisionItem(
        id=uuid.uuid4(),
        user_id=user_id,
        caption=payload.caption,
        image_mime=content_type,
        image_data=data,
        x=0.0,
        y=0.0,
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


@router.get("/{item_id}/image")
def get_vision_image(
    item_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Serves the image bytes, behind the owner's token."""
    item = owned_item(db, item_id, user_id)

    return Response(
        content=item.image_data,
        media_type=item.image_mime,
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.patch("/{item_id}", response_model=VisionItemOut)
def update_vision_item(
    item_id: uuid.UUID,
    payload: VisionItemUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Used by drag-and-drop to persist a new position."""
    item = owned_item(db, item_id, user_id)

    if payload.x is not None:
        item.x = payload.x

    if payload.y is not None:
        item.y = payload.y

    if payload.width is not None:
        item.width = payload.width

    if payload.caption is not None:
        item.caption = payload.caption.strip() or None

    db.commit()
    db.refresh(item)

    return item


@router.delete("/{item_id}")
def delete_vision_item(
    item_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    item = owned_item(db, item_id, user_id)

    db.delete(item)
    db.commit()

    return {"message": "Vision item deleted successfully"}

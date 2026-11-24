import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from auth import get_current_user_id
from database import get_db
from models import Note, NoteFolder
from schemas import (
    FolderCreate,
    FolderOut,
    FolderUpdate,
    NoteCreate,
    NoteOut,
    NoteUpdate,
    ReorderNotes,
)


router = APIRouter(tags=["notes"])


# ---- helpers ----


def owned_folder(db: Session, folder_id: uuid.UUID, user_id: uuid.UUID) -> NoteFolder:
    folder = db.scalar(
        select(NoteFolder).where(
            NoteFolder.id == folder_id,
            NoteFolder.user_id == user_id,
        )
    )

    if folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")

    return folder


def owned_note(db: Session, note_id: uuid.UUID, user_id: uuid.UUID) -> Note:
    note = db.scalar(
        select(Note).where(
            Note.id == note_id,
            Note.user_id == user_id,
        )
    )

    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    return note


# ---- folders ----


@router.get("/note-folders", response_model=list[FolderOut])
def get_folders(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    counts = dict(
        db.execute(
            select(Note.folder_id, func.count())
            .where(Note.user_id == user_id)
            .group_by(Note.folder_id)
        ).all()
    )

    folders = db.scalars(
        select(NoteFolder)
        .where(NoteFolder.user_id == user_id)
        .order_by(NoteFolder.name)
    ).all()

    return [
        FolderOut(
            id=folder.id,
            name=folder.name,
            created_at=folder.created_at,
            note_count=counts.get(folder.id, 0),
        )
        for folder in folders
    ]


@router.post("/note-folders", response_model=FolderOut)
def create_folder(
    payload: FolderCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    name = payload.name.strip()

    if not name:
        raise HTTPException(status_code=422, detail="Folder needs a name")

    duplicate = db.scalar(
        select(NoteFolder).where(
            NoteFolder.user_id == user_id,
            func.lower(NoteFolder.name) == name.lower(),
        )
    )

    if duplicate is not None:
        raise HTTPException(status_code=409, detail="You already have a folder with that name")

    folder = NoteFolder(id=uuid.uuid4(), user_id=user_id, name=name)

    db.add(folder)
    db.commit()
    db.refresh(folder)

    return FolderOut(
        id=folder.id,
        name=folder.name,
        created_at=folder.created_at,
        note_count=0,
    )


@router.patch("/note-folders/{folder_id}", response_model=FolderOut)
def rename_folder(
    folder_id: uuid.UUID,
    payload: FolderUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    folder = owned_folder(db, folder_id, user_id)

    if payload.name is not None:
        folder.name = payload.name.strip()

    db.commit()
    db.refresh(folder)

    count = db.scalar(
        select(func.count()).select_from(Note).where(Note.folder_id == folder.id)
    )

    return FolderOut(
        id=folder.id,
        name=folder.name,
        created_at=folder.created_at,
        note_count=count or 0,
    )


@router.delete("/note-folders/{folder_id}")
def delete_folder(
    folder_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Deletes the folder and its notes (ON DELETE CASCADE)."""
    folder = owned_folder(db, folder_id, user_id)

    db.delete(folder)
    db.commit()

    return {"message": "Folder deleted successfully"}


# ---- notes ----


@router.get("/notes", response_model=list[NoteOut])
def get_notes(
    folder_id: uuid.UUID | None = None,
    search: str | None = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """The timeline: pinned first, then newest first.

    Search is case-insensitive across title and body, and combines with the
    folder filter so "search inside this folder" works without extra endpoints.
    """
    query = select(Note).where(Note.user_id == user_id)

    if folder_id is not None:
        query = query.where(Note.folder_id == folder_id)

    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(Note.title.ilike(term), Note.body.ilike(term))
        )

    # Manual order first, then the date as a tie-break for notes that have
    # never been dragged (all position 0).
    query = query.order_by(
        Note.pinned.desc(),
        Note.position.asc(),
        Note.created_at.desc(),
    )

    return db.scalars(query).all()


@router.post("/notes", response_model=NoteOut)
def create_note(
    payload: NoteCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    # Proves the folder belongs to the caller before writing into it.
    owned_folder(db, payload.folder_id, user_id)

    note = Note(
        id=uuid.uuid4(),
        folder_id=payload.folder_id,
        user_id=user_id,
        title=payload.title.strip(),
        body=payload.body,
        pinned=payload.pinned,
    )

    db.add(note)
    db.commit()
    db.refresh(note)

    return note


@router.patch("/notes/{note_id}", response_model=NoteOut)
def update_note(
    note_id: uuid.UUID,
    payload: NoteUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    note = owned_note(db, note_id, user_id)

    # Moving between folders requires owning the destination too, or a note
    # could be pushed into someone else's drawer.
    if payload.folder_id is not None and payload.folder_id != note.folder_id:
        owned_folder(db, payload.folder_id, user_id)
        note.folder_id = payload.folder_id

    if payload.title is not None:
        note.title = payload.title.strip()

    if payload.body is not None:
        note.body = payload.body

    if payload.pinned is not None:
        note.pinned = payload.pinned

    # updated_at is the "edited" stamp; created_at stays the timeline anchor.
    note.updated_at = datetime.now()

    db.commit()
    db.refresh(note)

    return note


@router.post("/notes/reorder", response_model=list[NoteOut])
def reorder_notes(
    payload: ReorderNotes,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Saves a dragged order.

    The client sends the ids of one list in their new order; each gets a
    position of its index. created_at is never touched — the timeline is
    about when a note was written, and dragging must not rewrite history.

    Any id that is not the caller's is ignored rather than rejected, so a
    stale list from another tab cannot fail the whole reorder.
    """
    owned = {
        note.id: note
        for note in db.scalars(
            select(Note).where(
                Note.user_id == user_id,
                Note.id.in_(payload.note_ids),
            )
        ).all()
    }

    for index, note_id in enumerate(payload.note_ids):
        note = owned.get(note_id)

        if note is not None:
            note.position = index

    db.commit()

    return [
        owned[note_id]
        for note_id in payload.note_ids
        if note_id in owned
    ]


@router.delete("/notes/{note_id}")
def delete_note(
    note_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    note = owned_note(db, note_id, user_id)

    db.delete(note)
    db.commit()

    return {"message": "Note deleted successfully"}

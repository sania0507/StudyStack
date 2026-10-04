from fastapi import FastAPI,Depends,HTTPException
import uuid

from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from sqlalchemy import select
from sqlalchemy.orm import Session
from models import Base, Domain

from database import engine, SessionLocal



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class DomainCreate(BaseModel):
    name: str

class DomainUpdate(BaseModel):
    name: str | None = None
    colour: str | None = None

#Pydantic needs to be told that DomainOut can read attributes from an ORM object. 
#Now, pydantic can build a response from object's attributes like domain.name (from_attributes=true) instead of expecting a dictionary.
class DomainOut(BaseModel):
    id: uuid.UUID
    name: str
    colour: str

    model_config = {
        "from_attributes": True #
    }

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/domains", response_model=DomainOut)
def create_domain(
    domain: DomainCreate,
    db: Session = Depends(get_db)
):
    new_domain = Domain(
        id=uuid.uuid4(),
        name=domain.name,
        colour="violet",
    )

    db.add(new_domain)
    db.commit()

    return new_domain



@app.get("/domains", response_model=list[DomainOut])
def get_domains(db: Session = Depends(get_db)):
    result = db.execute(select(Domain))
    return result.scalars().all()

@app.patch("/domains/{domain_id}", response_model=DomainOut)
def update_domain(
    domain_id: uuid.UUID,
    domain: DomainUpdate,
    db: Session = Depends(get_db)
):
    existing_domain = db.get(Domain, domain_id)

    if existing_domain is None:
        raise HTTPException(
            status_code=404,
            detail="Domain not found"
        )

    if domain.name is not None:
        existing_domain.name = domain.name

    if domain.colour is not None:
        existing_domain.colour = domain.colour

    db.commit()
    db.refresh(existing_domain)

    return existing_domain

@app.delete("/domains/{domain_id}")
def delete_domain(
    domain_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    existing_domain = db.get(Domain, domain_id)

    if existing_domain is None:
        raise HTTPException(
            status_code=404,
            detail="Domain not found"
        )

    db.delete(existing_domain)
    db.commit()

    return {"message": "Domain deleted successfully"}
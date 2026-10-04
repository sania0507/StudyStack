from fastapi import FastAPI,Depends
from pydantic import BaseModel
import uuid
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, SessionLocal
from models import Base, Domain

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class DomainCreate(BaseModel):
    name: str

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/domains")
def create_domain( domain: DomainCreate, db: Session = Depends(get_db)):
    new_domain = Domain(
        id=uuid.uuid4(),
        name=domain.name,
        colour="violet",
    )

    db.add(new_domain)
    db.commit()

    return {
        "id": str(new_domain.id),
        "name": new_domain.name,
        "colour": new_domain.colour,
    }
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models.database import engine
from models.models import Base
from api import auth, shifts, employee, me , projects ,assignments , holidays ,allowance

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(redirect_slashes=False)

cors_origins = os.getenv("CORS_ORIGINS", "")

origins = [origin.strip() for origin in cors_origins.split(",") if origin]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       
    allow_credentials=True,       
    allow_methods=["*"],
    allow_headers=["*"],     
)

app.include_router(auth.router)
app.include_router(shifts.router)
app.include_router(me.router)
app.include_router(employee.router)
app.include_router(assignments.router)
app.include_router(projects.router)
app.include_router(holidays.router)
app.include_router(allowance.router)


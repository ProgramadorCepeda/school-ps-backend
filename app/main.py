import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Session, select

from app.core.config import get_settings
from app.core.db import engine
from app.modules import router
from app.modules.enrollment.infrastructure.models import Grado

# Import all model modules to register them in SQLModel metadata
import app.modules.auth.infrastructure.models
import app.modules.cafeteria.infrastructure.models
import app.modules.chess.infrastructure.models
import app.modules.classroom.infrastructure.models
import app.modules.classroom_holder.infrastructure.models
import app.modules.enrollment.infrastructure.models
import app.modules.inventory.infrastructure.models

try:
    import app.modules.peace_safe.infrastructure.models
except ImportError:
    pass
import app.modules.principal.infrastructure.models
import app.modules.tests.infrastructure.models
import app.modules.training_schools.infrastructure.models
import app.modules.tuition.infrastructure.models

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if "pytest" not in sys.modules:
        # Ensure all tables exist in the database
        SQLModel.metadata.create_all(engine)

        # Ensure all default school grades exist
        default_grades = [
            "Preescolar",
            "Primero",
            "Segundo",
            "Tercero",
            "Cuarto",
            "Quinto",
            "Sexto",
            "Séptimo",
            "Octavo",
            "Noveno",
            "Décimo",
            "Once",
        ]
        with Session(engine) as session:
            for grade_name in default_grades:
                statement = select(Grado).where(Grado.nombre == grade_name)
                existing = session.exec(statement).first()
                if not existing:
                    session.add(Grado(nombre=grade_name))
            session.commit()

    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.allow_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

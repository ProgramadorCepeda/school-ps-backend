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
from app.modules.auth.infrastructure import models as auth_models  # noqa: F401
from app.modules.cafeteria.infrastructure import models as cafeteria_models  # noqa: F401
from app.modules.chess.infrastructure import models as chess_models  # noqa: F401
from app.modules.classroom.infrastructure import models as classroom_models  # noqa: F401
from app.modules.classroom_holder.infrastructure import (
    models as classroom_holder_models,  # noqa: F401
)
from app.modules.enrollment.infrastructure import models as enrollment_models  # noqa: F401
from app.modules.inventory.infrastructure import models as inventory_models  # noqa: F401

try:
    from app.modules.peace_safe.infrastructure import models as peace_safe_models  # noqa: F401
except ImportError:
    pass
from app.modules.principal.infrastructure import models as principal_models  # noqa: F401
from app.modules.tests.infrastructure import models as tests_models  # noqa: F401
from app.modules.training_schools.infrastructure import (
    models as training_schools_models,  # noqa: F401
)
from app.modules.tuition.infrastructure import models as tuition_models  # noqa: F401

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

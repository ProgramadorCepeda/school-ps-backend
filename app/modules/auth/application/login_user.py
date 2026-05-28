from sqlmodel import Session, select

from app.modules.auth.infrastructure.models import Usuario
from app.modules.auth.schemas.request import LoginRequest


class LoginUser:
    """Caso de uso: autenticar un usuario y validar su rol."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def execute(self, request: LoginRequest) -> tuple[Usuario, str, str]:
        statement = select(Usuario).where(
            Usuario.username == request.username,
            Usuario.contrasenia == request.contrasenia,
        )
        user = self.session.exec(statement).first()

        if not user:
            msg = "Nombre de usuario o contraseña incorrectos"
            raise ValueError(msg)

        if not user.estado:
            msg = "El usuario se encuentra inactivo"
            raise ValueError(msg)

        # Normalizar el rol a uno de los 4 permitidos: Rectoría, Administración, Tesorería, Docente
        role_lower = user.rol.lower().strip()
        if "rector" in role_lower:
            normalized_role = "Rectoría"
        elif "docente" in role_lower:
            normalized_role = "Docente"
        elif "tesor" in role_lower or "matrícula" in role_lower or "matricula" in role_lower or "paz" in role_lower:
            normalized_role = "Tesorería"
        else:
            normalized_role = "Administración"

        # Generamos un token de sesión sencillo (ej: token_rol_username_id)
        token = f"session_token_{normalized_role}_{user.username}_{user.id}"

        return user, token, normalized_role

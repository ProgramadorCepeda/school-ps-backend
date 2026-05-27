from sqlmodel import Session, select

from app.modules.auth.infrastructure.models import Usuario
from app.modules.auth.schemas.request import LoginRequest


class LoginUser:
    """Caso de uso: autenticar un usuario y validar su rol."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def execute(self, request: LoginRequest) -> tuple[Usuario, str]:
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

        # Generamos un token de sesión sencillo (ej: token_rol_username_id)
        # Esto sirve para que el frontend lo guarde y sepa qué rol tiene el usuario.
        token = f"session_token_{user.rol}_{user.username}_{user.id}"

        return user, token

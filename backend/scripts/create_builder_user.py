"""
Crea (o convierte) una cuenta Builder. No hay autorregistro: solo se hace así.

Uso:
    python scripts/create_builder_user.py correo@ejemplo.com contraseña ["Nombre completo"]
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal, engine, Base
from app.models.models import User, RoleEnum
from app.core.security import hash_password


def crear_builder(email: str, password: str, full_name: str | None = None) -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existente = db.query(User).filter(User.email == email).first()
        if existente:
            existente.role = RoleEnum.builder
            existente.hashed_password = hash_password(password)
            if full_name:
                existente.full_name = full_name
            db.commit()
            print(f"Usuario existente convertido a Builder: {email}")
            return

        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=RoleEnum.builder,
        )
        db.add(user)
        db.commit()
        print(f"Builder creado: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('Uso: python scripts/create_builder_user.py correo contraseña ["Nombre completo"]')
        sys.exit(1)
    crear_builder(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)

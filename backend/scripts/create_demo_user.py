from pathlib import Path
import sys

# Asegurar que el paquete `app` es importable cuando se ejecuta desde la raíz
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal, engine, Base
from app.models.models import User, RoleEnum
from app.core.security import hash_password


def create_demo_user():
    # ensure tables exist (convenience for local/dev)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        email = "demo@example.com"
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"Usuario demo ya existe: {existing.email}")
            return

        user = User(
            email=email,
            full_name="Usuario Demo",
            hashed_password=hash_password("demo1234"),
            role=RoleEnum.owner,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print("Usuario demo creado:", email)
        print("Contraseña: demo1234")
    finally:
        db.close()


if __name__ == "__main__":
    create_demo_user()

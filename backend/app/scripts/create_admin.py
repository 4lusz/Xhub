"""Cria um usuário administrador para o XHub."""

import getpass

from app.database.session import SessionLocal
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService


def main() -> None:
    db = SessionLocal()

    try:
        user_repository = UserRepository(db)
        user_service = UserService(user_repository)

        print("\n=== Criar Administrador XHub ===\n")

        name = input("Nome: ").strip()
        email = input("E-mail: ").strip()
        password = getpass.getpass("Senha: ")

        existing_user = user_repository.get_by_email(email)

        if existing_user is not None:
            print("\nJá existe um usuário com esse e-mail.")
            return

        user_service.create_user(
            name=name,
            email=email,
            password=password,
            role=UserRole.ADMIN,
        )

        db.commit()

        print("\nAdministrador criado com sucesso!")
        print(f"Nome : {name}")
        print(f"E-mail: {email}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
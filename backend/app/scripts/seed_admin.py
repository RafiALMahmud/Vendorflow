import argparse
from getpass import getpass

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import select

from app.core.auth import hash_password
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.identity import User, UserRole
from app.schemas.auth import normalize_email


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed a local VendorFlow admin")
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    return parser.parse_args()


def main() -> int:
    settings = get_settings()
    if settings.app_env not in {"development", "test"}:
        raise SystemExit("Admin seeding is restricted to development/test environments")

    args = parse_args()
    try:
        email = normalize_email(
            validate_email(args.email, check_deliverability=False).normalized
        )
    except EmailNotValidError as exc:
        raise SystemExit(f"Invalid email: {exc}") from exc

    password = getpass("Admin password (12-128 characters): ")
    confirmation = getpass("Confirm admin password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")
    if not 12 <= len(password) <= 128:
        raise SystemExit("Password must contain 12-128 characters")
    full_name = args.full_name.strip()
    if not full_name:
        raise SystemExit("Full name cannot be blank")

    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)) is not None:
            raise SystemExit("A user with this email already exists")
        db.add(
            User(
                email=email,
                full_name=full_name,
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
            )
        )
        db.commit()

    print(f"Created local admin account for {email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

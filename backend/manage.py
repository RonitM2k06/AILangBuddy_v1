"""Out-of-band admin creation (self-registration can never produce an admin).

    .venv/bin/python -m backend.manage create-admin --email you@example.com --name "Your Name"

The password is prompted for and never passed on the command line.
"""
import argparse
import getpass
import os
from pathlib import Path

from .auth import service
from .db.migrate import migrate


def create_admin(db_path, email, password, display_name):
    migrate(db_path)
    user, _ = service.create_user(db_path, email=email, password=password, display_name=display_name,
                                  roles=["admin"], with_session=False)
    return user


def main(argv=None):
    parser = argparse.ArgumentParser(prog="backend.manage")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("create-admin")
    p.add_argument("--email", required=True)
    p.add_argument("--name", default="Admin")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    db_path = Path(os.getenv("DB_PATH", root / "buddy.db"))
    password = getpass.getpass("Password (min 8 chars): ")
    if len(password) < 8 or password != getpass.getpass("Repeat password: "):
        raise SystemExit("Passwords must match and be at least 8 characters.")
    try:
        user = create_admin(db_path, args.email, password, args.name)
    except service.EmailTaken:
        raise SystemExit("That email is already registered.")
    print(f"Created admin {user.email} (handle {user.handle})")


if __name__ == "__main__":
    main()

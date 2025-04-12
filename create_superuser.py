from sqlalchemy.orm import Session
from database import SessionLocal
from models import User
from auth import hash_password

# 👇 Customize your superuser credentials here
SUPERUSER_PHONE = "12345678"
SUPERUSER_PASSWORD = "098765"

db: Session = SessionLocal()

# Check if the superuser already exists
existing_user = db.query(User).filter(User.phone == SUPERUSER_PHONE).first()
if existing_user:
    print("Superuser already exists.")
else:
    new_user = User(
        phone=SUPERUSER_PHONE,
        password=hash_password(SUPERUSER_PASSWORD),
        # Optionally add a boolean field like is_superuser=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    print(f"Superuser created with phone: {SUPERUSER_PHONE}")

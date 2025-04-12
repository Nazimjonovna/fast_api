from random import randint
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import json
import os
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from models import User, Product
from schemas import UserCreate, UserInDB, Token, smsUser, ProductSchema, ProductCreate
from database import SessionLocal
from auth import create_access_token, verify_password, hash_password, verify_token
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

UPLOAD_DIR = Path("uploaded_images") 
UPLOAD_DIR.mkdir(parents=True, exist_ok=True) 

origins = [
    "http://localhost:3000", 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def sms_code():
    return randint(100000, 999999)

def save_file(file: UploadFile, folder: str = "uploads") -> str:
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    file_path = os.path.join(folder, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return file_path


@app.post('/sms_code/')
def get_sms(user: smsUser, db: Session = Depends(get_db)):
    code = sms_code()
    db_user = db.query(User).filter(User.phone == user.phone).first()
    if not db_user:
        db_user = User(phone=user.phone)
    db_user.sms_cod = code 
    db_user.password = user.password
    db.add(db_user)
    db.commit()
    return HTTPException(status_code=200, detail = f"your code : {code}")


@app.post("/register/", response_model=UserInDB)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    current_user = db.query(User).filter(User.phone == user.phone).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")
    if current_user.sms_cod != user.sms_cod:
        raise HTTPException(status_code=400, detail="SMS code xato kiritdingiz")
    current_user.hashed_password = hash_password(user.password)
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@app.post("/login/", response_model=Token)
def login_user(user: smsUser, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.phone == user.phone).first()
    print(db_user)
    print("password", user.password)
    print("hash", db_user.password)
    if db_user is None or not verify_password(user.password, db_user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    access_token = create_access_token(data={"sub": user.phone})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/profile/me", response_model=UserInDB)
def get_me(id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=200, detail = "User not found")
    return user


@app.get('/profile/users', response_model=UserInDB)
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    if not users:
        raise HTTPException(status_code=200, detail="Users not found")
    return users


@app.patch("/profile/edit/{user_id}")
def update_user(user_id: int, user_update: smsUser, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if user_update.name:
        db_user.name = user_update.name
    if user_update.password:
        db_user.password = hash_password(user_update.password)
    db.commit()
    db.refresh(db_user)
    return {"message": "User updated successfully", "user": db_user}


@app.delete("/profile/delete/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return


@app.post('/product/create/', response_model=ProductCreate)
def create_product(
    product: str = Form(...),  
    picture: UploadFile = File(...),  
    db: Session = Depends(get_db)
):
    try:
        product_data = json.loads(product) 
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid product JSON")
    product_schema = ProductCreate(**product_data)
    existing_product = db.query(Product).filter(Product.name == product_schema.name).first()
    if existing_product:
        raise HTTPException(status_code=400, detail="Product with this name already exists")
    picture_filename = f"{product_schema.name}_{picture.filename}"
    picture_path = UPLOAD_DIR / picture_filename
    
    with picture_path.open("wb") as buffer:
        shutil.copyfileobj(picture.file, buffer)
    
    new_product = Product(
        name=product_schema.name,
        cost=product_schema.cost,
        number=product_schema.number,
        picture=str(picture_path)  
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product


@app.get("/product/{product_id}", status_code=status.HTTP_200_OK)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=200, detail = "Product not found")
    return product


@app.patch("/product/edit/{product_id}")
def update_product(
    product_id: int,
    product_edit: ProductSchema,
    picture: UploadFile = File(None), 
    db: Session = Depends(get_db)
):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product_edit.name:
        db_product.name = product_edit.name
    if product_edit.cost:
        db_product.cost = product_edit.cost
    if product_edit.number:
        db_product.number = product_edit.number
    if picture:
        file_path = save_file(picture)  
        db_product.picture = file_path 
    db.commit()
    db.refresh(db_product)
    return {"message": "Product updated successfully", "product": db_product}


@app.delete("/product/delete/{product_id}", status_code=status.HTTP_200_OK)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_product)
    db.commit()
    return
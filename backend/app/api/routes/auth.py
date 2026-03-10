from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from ...database import get_db
from ...models import User, UserPreferences
from ...schemas import UserCreate, UserLogin, Token, UserResponse
from ...utils.auth import auth_service

router = APIRouter()

# Use auth service methods
verify_password = auth_service.verify_password
get_password_hash = auth_service.get_password_hash
create_access_token = auth_service.create_access_token
get_current_user = auth_service.get_current_user

@router.post("/register", response_model=Token)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        organization=user_data.organization
    )
    db.add(db_user)
    
    # Create user preferences
    db_preferences = UserPreferences(user_id=db_user.id)
    db.add(db_preferences)
    
    db.commit()
    db.refresh(db_user)
    
    # Create access token
    access_token = create_access_token(data={"sub": str(db_user.id)})
    
    return Token(
        access_token=access_token,
        user=UserResponse.model_validate(db_user)
    )

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    # Authenticate user
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return Token(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    # Stateless JWT — client-side token removal handles logout
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)
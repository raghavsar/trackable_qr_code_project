from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from services.auth import AuthService
from models.user import UserResponse, UserUpdate
from datetime import datetime

router = APIRouter()

@router.put("/profile", response_model=UserResponse)
async def update_profile(
    update_data: UserUpdate,
    current_user: Annotated[UserResponse, Depends(AuthService.get_current_user)],
    auth_service: AuthService = Depends()
):
    """Update current user's profile."""
    try:
        # Don't allow email updates for Google users
        if current_user.auth_provider == "google" and update_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update email for Google accounts"
            )

        updated_user = await auth_service.update_user_profile(
            user_id=current_user.id,
            update_data=update_data
        )
        return updated_user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/password")
async def update_password(
    current_password: str,
    new_password: str,
    current_user: Annotated[UserResponse, Depends(AuthService.get_current_user)],
    auth_service: AuthService = Depends()
):
    """Update current user's password."""
    try:
        # Don't allow password updates for Google users
        if current_user.auth_provider == "google":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update password for Google accounts"
            )

        await auth_service.update_user_password(
            user_id=current_user.id,
            current_password=current_password,
            new_password=new_password
        )
        return {"message": "Password updated successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/me")
async def delete_account(
    current_user: Annotated[UserResponse, Depends(AuthService.get_current_user)],
    auth_service: AuthService = Depends()
):
    """Delete current user's account."""
    try:
        await auth_service.delete_user(current_user.id)
        return {"message": "Account deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 
"""
File: app/api/v1/routers/auth.py
Folder: backend/app/api/v1/routers
Purpose: HTTP layer for authentication. Routes contain no business logic —
         they parse/validate input, call AuthService, and shape the
         response. All errors are domain exceptions raised by the service
         and handled globally (see core/exceptions.py).
"""

from typing import Annotated



from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.api.v1.deps import get_auth_service, get_current_user, get_email_verification_service
from app.application.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResendVerificationRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.application.services.auth_service import AuthService
from app.application.services.email_verification_service import EmailVerificationService
from app.core.rate_limit import resend_verification_rate_limiter
from app.domain.entities.user import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    verification_service: Annotated[EmailVerificationService, Depends(get_email_verification_service)],
) -> User:
    user = auth_service.register(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        company_name=payload.company_name,
        sector=payload.sector,
    )
    verification_service.send_verification_code(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    user = auth_service.authenticate(email=payload.email, password=payload.password)
    access_token, refresh_token = auth_service.issue_tokens(user)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    access_token, refresh_token = auth_service.refresh_access_token(payload.refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: RefreshRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    auth_service.logout(current_user.id, payload.refresh_token)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@router.post("/me/photo", response_model=UserResponse)
async def upload_profile_photo(
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    file: UploadFile = File(...),
) -> User:
    content = await file.read()
    return auth_service.update_profile_photo(
        current_user.id, content, file.content_type or "application/octet-stream"
    )


@router.delete("/me/photo", response_model=UserResponse)
def delete_profile_photo(
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    return auth_service.remove_profile_photo(current_user.id)

@router.post("/verify-email", response_model=UserResponse)
def verify_email(
    payload: VerifyEmailRequest,
    verification_service: Annotated[EmailVerificationService, Depends(get_email_verification_service)],
) -> User:
    return verification_service.verify_code(payload.user_id, payload.code)


@router.post("/resend-verification", response_model=UserResponse)
def resend_verification(
    payload: ResendVerificationRequest,
    request: Request,
    verification_service: Annotated[EmailVerificationService, Depends(get_email_verification_service)],
) -> User:
    client_ip = request.client.host if request.client else "unknown"
    if not resend_verification_rate_limiter.allow(client_ip):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests. Try again later.")
    return verification_service.resend_code(payload.email)
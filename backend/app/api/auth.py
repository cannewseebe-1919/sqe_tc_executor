"""SAML 2.0 SSO authentication endpoints."""

import logging

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, Response

from onelogin.saml2.auth import OneLogin_Saml2_Auth

from app.core.auth import create_jwt_token, get_saml_settings, prepare_saml_request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _init_saml_auth(req_data: dict) -> OneLogin_Saml2_Auth:
    saml_settings = get_saml_settings()
    if not saml_settings:
        raise HTTPException(status_code=500, detail="SAML not configured")
    return OneLogin_Saml2_Auth(req_data, saml_settings)


@router.post("/dev-login")
async def dev_login():
    """Dev-mode only: returns a JWT token without any authentication."""
    from app.core.config import get_settings
    if not get_settings().DEV_MODE:
        raise HTTPException(status_code=403, detail="Dev login is disabled in production")
    from app.core.auth import create_jwt_token, DEV_USER
    token = create_jwt_token(DEV_USER)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/saml/login")
async def saml_login(request: Request):
    """Initiate SAML SSO login — redirect to IdP."""
    req_data = prepare_saml_request(request)
    auth = _init_saml_auth(req_data)
    sso_url = auth.login()
    return RedirectResponse(url=sso_url)


@router.post("/saml/acs")
async def saml_acs(request: Request):
    """SAML Assertion Consumer Service — process IdP response."""
    form_data = await request.form()
    req_data = prepare_saml_request(request)
    req_data["post_data"] = dict(form_data)

    auth = _init_saml_auth(req_data)
    auth.process_response()

    errors = auth.get_errors()
    if errors:
        logger.error("SAML validation errors: %s", errors)
        raise HTTPException(status_code=400, detail=f"SAML Error: {', '.join(errors)}")

    if not auth.is_authenticated():
        raise HTTPException(status_code=401, detail="SAML authentication failed")

    attributes = auth.get_attributes()
    name_id = auth.get_nameid()

    token = create_jwt_token({
        "sub": name_id,
        "email": name_id,
        "name": attributes.get("displayName", [name_id])[0],
        "department": attributes.get("department", [None])[0],
    })

    # Redirect to frontend with token
    return RedirectResponse(url=f"/auth/callback?token={token}")


@router.get("/saml/slo")
async def saml_slo(request: Request):
    """Initiate Single Logout."""
    req_data = prepare_saml_request(request)
    auth = _init_saml_auth(req_data)
    slo_url = auth.logout()
    return RedirectResponse(url=slo_url)


@router.get("/saml/metadata")
async def saml_metadata(request: Request):
    """SP metadata for IdP registration."""
    req_data = prepare_saml_request(request)
    auth = _init_saml_auth(req_data)
    metadata = auth.get_settings().get_sp_metadata()
    errors = auth.get_settings().validate_metadata(metadata)
    if errors:
        raise HTTPException(status_code=500, detail=f"Metadata error: {', '.join(errors)}")
    return Response(content=metadata, media_type="application/xml")

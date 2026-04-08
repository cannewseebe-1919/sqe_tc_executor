"""SAML 2.0 SSO authentication endpoints."""

from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse

from app.core.auth import create_jwt_token, get_saml_settings, prepare_saml_request

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/saml/login")
async def saml_login(request: Request):
    """Initiate SAML login — redirect to IdP."""
    saml_settings = get_saml_settings()
    if not saml_settings:
        return {"error": "SAML not configured"}

    # In production, use python3-saml to create AuthnRequest
    # For now, redirect to IdP SSO URL
    idp_sso_url = saml_settings.get("idp", {}).get("singleSignOnService", {}).get("url", "")
    if not idp_sso_url:
        return {"error": "IdP SSO URL not configured"}
    return RedirectResponse(url=idp_sso_url)


@router.post("/saml/acs")
async def saml_acs(request: Request):
    """SAML Assertion Consumer Service — receives SAML Response from IdP."""
    form_data = await request.form()
    saml_response = form_data.get("SAMLResponse", "")

    if not saml_response:
        return {"error": "No SAMLResponse received"}

    # In production: validate SAML Response with python3-saml
    # Extract user attributes from SAML Assertion
    # For now, create a JWT token with placeholder user info
    # TODO: Integrate python3-saml for full SAML validation
    user_data = {
        "email": "user@company.com",
        "name": "Test User",
        "department": "QA",
    }
    token = create_jwt_token(user_data)
    return {"token": token, "user": user_data}


@router.get("/saml/metadata")
async def saml_metadata():
    """Return SP SAML metadata XML."""
    saml_settings = get_saml_settings()
    if not saml_settings:
        return Response(content="SAML not configured", media_type="text/plain")
    # In production: generate SP metadata XML using python3-saml
    return Response(content="<EntityDescriptor/>", media_type="application/xml")


@router.post("/saml/slo")
async def saml_slo(request: Request):
    """Single Logout endpoint."""
    return {"status": "logged_out"}

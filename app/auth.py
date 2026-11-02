from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets
import jwt
from jwt import PyJWKClient, InvalidTokenError
from fastapi import Header, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials, HTTPBearer, HTTPAuthorizationCredentials
from .config import settings

basic_scheme=HTTPBasic(auto_error=False)
bearer_scheme=HTTPBearer(auto_error=False)
_jwks_client=None

def deny(status=401,detail="Invalid or missing credentials"):
    raise HTTPException(status_code=status,detail=detail,headers={"WWW-Authenticate":"Bearer"})

def api_key(x_api_key: Optional[str]=Header(default=None)):
    if not x_api_key or not secrets.compare_digest(x_api_key,settings.api_key): deny()

def basic(credentials: Optional[HTTPBasicCredentials]=Depends(basic_scheme)):
    if not credentials: deny()
    if not (secrets.compare_digest(credentials.username,settings.basic_username) and secrets.compare_digest(credentials.password,settings.basic_password)): deny()
    return {"sub":credentials.username,"auth":"basic"}

def bearer_credentials(credentials: Optional[HTTPAuthorizationCredentials]=Depends(bearer_scheme)):
    if not credentials: deny()
    return credentials.credentials

def static_bearer(token: str=Depends(bearer_credentials)):
    if not secrets.compare_digest(token,settings.static_bearer_token): deny()
    return {"sub":"static-demo-token","auth":"static-bearer"}

def issue_local_token(client_id,client_secret):
    if not (secrets.compare_digest(client_id,settings.oauth_client_id) and secrets.compare_digest(client_secret,settings.oauth_client_secret)): deny()
    now=datetime.now(timezone.utc)
    claims={"iss":"adf-mock-local-issuer","aud":"adf-mock-api","sub":client_id,
            "iat":now,"exp":now+timedelta(seconds=settings.oauth_token_ttl_seconds),
            "scope":"Data.Read Data.Write","roles":["Data.Read.All","Data.Write.All"]}
    return jwt.encode(claims,settings.oauth_signing_secret,algorithm="HS256")

def local_oauth(token: str=Depends(bearer_credentials)):
    try:
        return jwt.decode(token,settings.oauth_signing_secret,algorithms=["HS256"],audience="adf-mock-api",issuer="adf-mock-local-issuer")
    except InvalidTokenError: deny()

def entra(token: str=Depends(bearer_credentials)):
    if not settings.entra_tenant_id or not settings.entra_audience:
        raise HTTPException(501,"Configure ENTRA_TENANT_ID and ENTRA_AUDIENCE in .env before using Entra authentication.")
    global _jwks_client
    jwks_url=f"https://login.microsoftonline.com/{settings.entra_tenant_id}/discovery/v2.0/keys"
    try:
        if _jwks_client is None: _jwks_client=PyJWKClient(jwks_url)
        key=_jwks_client.get_signing_key_from_jwt(token).key
        opts={"verify_aud":True,"verify_iss":bool(settings.entra_issuer)}
        claims=jwt.decode(token,key,algorithms=["RS256"],audience=settings.entra_audience,
                          issuer=settings.entra_issuer if settings.entra_issuer else None,options=opts)
        scopes=claims.get("scp","").split()
        roles=claims.get("roles",[])
        if settings.entra_required_scope not in scopes and settings.entra_required_role not in roles:
            deny(403,"Token valid but required scope or app role is missing")
        return claims
    except HTTPException: raise
    except Exception: deny()

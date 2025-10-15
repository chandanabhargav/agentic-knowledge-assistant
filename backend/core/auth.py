from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from backend.core.settings import settings

security = HTTPBearer(auto_error=False)

def bearer_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if settings.BEARER_TOKEN and credentials and credentials.scheme.lower() == "bearer":
        if credentials.credentials == settings.BEARER_TOKEN:
            return True
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

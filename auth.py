import secrets
import time

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken


class EshipzOAuthProvider(
    OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]
):
    def __init__(self):
        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._authorization_codes: dict[str, AuthorizationCode] = {}
        self._access_tokens: dict[str, AccessToken] = {}
        self._refresh_tokens: dict[str, RefreshToken] = {}

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self._clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        if not client_info.client_id:
            client_info.client_id = secrets.token_urlsafe(24)
            client_info.client_id_issued_at = int(time.time())
        self._clients[client_info.client_id] = client_info

    async def authorize(self, client: OAuthClientInformationFull, params) -> str:
        code = secrets.token_urlsafe(32)
        expires_at = time.time() + 300
        scopes = params.scopes or ["eshipz"]

        auth_code = AuthorizationCode(
            code=code,
            scopes=scopes,
            expires_at=expires_at,
            client_id=client.client_id or "",
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=params.resource,
        )
        self._authorization_codes[code] = auth_code

        return construct_redirect_uri(
            str(params.redirect_uri),
            code=code,
            state=params.state,
        )

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        code = self._authorization_codes.get(authorization_code)
        if not code:
            return None

        if code.client_id != (client.client_id or ""):
            return None

        if code.expires_at < time.time():
            self._authorization_codes.pop(authorization_code, None)
            return None

        return code

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        self._authorization_codes.pop(authorization_code.code, None)

        access_token_value = secrets.token_urlsafe(32)
        refresh_token_value = secrets.token_urlsafe(32)
        expires_in = 3600
        expires_at = int(time.time()) + expires_in

        access_token = AccessToken(
            token=access_token_value,
            client_id=authorization_code.client_id,
            scopes=authorization_code.scopes,
            expires_at=expires_at,
            resource=authorization_code.resource,
        )
        refresh_token = RefreshToken(
            token=refresh_token_value,
            client_id=authorization_code.client_id,
            scopes=authorization_code.scopes,
        )

        self._access_tokens[access_token_value] = access_token
        self._refresh_tokens[refresh_token_value] = refresh_token

        return OAuthToken(
            access_token=access_token_value,
            token_type="Bearer",
            expires_in=expires_in,
            scope=" ".join(authorization_code.scopes),
            refresh_token=refresh_token_value,
        )

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        token = self._refresh_tokens.get(refresh_token)
        if token and token.client_id == (client.client_id or ""):
            return token
        return None

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        self._refresh_tokens.pop(refresh_token.token, None)

        scope_list = scopes or refresh_token.scopes
        access_token_value = secrets.token_urlsafe(32)
        refresh_token_value = secrets.token_urlsafe(32)
        expires_in = 3600
        expires_at = int(time.time()) + expires_in

        new_access_token = AccessToken(
            token=access_token_value,
            client_id=refresh_token.client_id,
            scopes=scope_list,
            expires_at=expires_at,
        )
        new_refresh_token = RefreshToken(
            token=refresh_token_value,
            client_id=refresh_token.client_id,
            scopes=scope_list,
        )

        self._access_tokens[access_token_value] = new_access_token
        self._refresh_tokens[refresh_token_value] = new_refresh_token

        return OAuthToken(
            access_token=access_token_value,
            token_type="Bearer",
            expires_in=expires_in,
            scope=" ".join(scope_list),
            refresh_token=refresh_token_value,
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        access_token = self._access_tokens.get(token)
        if not access_token:
            return None

        if access_token.expires_at is not None and access_token.expires_at < int(time.time()):
            self._access_tokens.pop(token, None)
            return None

        return access_token

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        if isinstance(token, AccessToken):
            self._access_tokens.pop(token.token, None)
        else:
            self._refresh_tokens.pop(token.token, None)

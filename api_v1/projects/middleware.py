from starlette.authentication import (
	AuthenticationBackend,
	AuthCredentials,
	UnauthenticatedUser as UnauthenticatedUserBase,
	AuthenticationError
)
from starlette.middleware.base import BaseHTTPMiddleware
from tortoise.query_utils import Prefetch
from fastapi import Request

from api_v1.projects.functions import (
	get_current_user
)
from api_v1.projects.models import Token, User

class UnauthenticatedUser(UnauthenticatedUserBase):

	def is_authenticated(
		self: 'UnauthenticatedUser'
	) -> bool:
		return False

class JWTCookieAuthBackend(AuthenticationBackend):
	
	async def authenticate(
		self: 'JWTCookieAuthBackend',
		request: Request
	) -> tuple[AuthCredentials, UnauthenticatedUser] | tuple[AuthCredentials, User]:
		token_in_cookies: bool = 'token' in request.cookies

		unauthenticated: tuple[AuthCredentials, UnauthenticatedUser] = AuthCredentials(), UnauthenticatedUser()

		if not any([token_in_cookies]):
			return unauthenticated ## the user isn't authenticated. return a blank AuthCredentials and empty object

		user = None

		if token_in_cookies:
			auth: str = request.cookies['token']
			
			try:
				user: User = await get_current_user(auth) ## try get the user using the token
			except Exception as e:
				if 'logout' in request.url.path:
					pass
				else:
					raise AuthenticationError from e
		
		if user is None: ## JWT's invalid
			return unauthenticated ## the user isn't authenticated. return a blank AuthCredentials and empty object

		return AuthCredentials(['authenticated']), user # return the users permissions and the user object
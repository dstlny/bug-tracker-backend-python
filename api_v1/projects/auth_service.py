from fastapi import (
	APIRouter,
	Request,
	Depends,
	HTTPException,
	status,
	Form, 
	Body,
	Response,
	WebSocket,
	Cookie,
	Query
)
from fastapi.responses import (
	RedirectResponse
)
from fastapi.websockets import WebSocketDisconnect
from starlette.authentication import (
	requires,
	UnauthenticatedUser
)

from tortoise.timezone import now
from sse_starlette.sse import EventSourceResponse

from datetime import timedelta
import re
import typing
import json
import asyncio 
from dateutil import parser
import bleach
import os

import api_v1.projects.settings as auth_settings
from api_v1.projects.functions import *
from api_v1.projects.route_models import *
from api_v1.projects.models import (
	Token,
	User,
)
from api_v1.projects.settings import (
	AUTH_SECRET_KEY,
	AUTH_ALGORITHM
)
from api_v1.settings import get_settings
from api_v1.base_service import Service
from api_v1.pydantic.models import (
	User_Pydantic,
	UserListing_Pydantic
)
from api_v1.decorators import (
	requires_login,
	cache_route
)
from typing import (
	List,
	Dict
)

password_regex = re.compile('^(?=.*?[A-Z])(?=.*?[a-z])(?=.*?[0-9])(?=.*?[#?!@$%^&*-]).{8,}$')


class AuthService(Service):

	def install(self):

		@self.router.get('/users/')
		@cache_route(
			app = self.app
		)
		async def get_users(
			request: Request
		) -> UserListing_Pydantic:

			return await UserListing_Pydantic.from_queryset(
				queryset = User.all()
			)


		@self.router.post("/login/")
		async def login(
			request: Request,
			response: Response,
			form_data: Optional[RouteLogin] = Optional[None]
		):

			if hasattr(request.user, 'pk'):

				user: User = request.user

			else:

				if form_data:
					pass
				else:
					return {
						'message': 'Not Authenticated'
					}

				access_token_expires = timedelta(
					minutes=auth_settings.AUTH_ACCESS_TOKEN_EXPIRE_MINUTES
				)

				user: User = await User._authenticate_user(form_data.username, form_data.password)

				access_token, expiry = create_access_token(
					data={"sub": str(user.pk)}, expires_delta=access_token_expires
				)

				await Token.create(
					token=access_token,
					expires=expiry,
					user_id=user.pk,
					secret=AUTH_SECRET_KEY,
					algorithm=AUTH_ALGORITHM
				)

				total_seconds: int = access_token_expires.total_seconds()

				response.set_cookie(
					key="token",
					value=access_token,
					max_age=total_seconds,
					expires=total_seconds
				)

			return await User_Pydantic.from_tortoise_orm(user)

		@self.router.post("/logout/")
		async def logout(
			request: Request,
			response: Response,
		):

			token = request.cookies.get('token')

			tokens: list[str] = []

			if token is not None:
				tokens.append(token)

			token_in_db = await Token.filter(
				token__in=tokens
			).update(
				force_expiration=True
			)

			for key, value in {'token': None}.items():
				response.set_cookie(
					key=key,
					value=value,
					max_age=0,
					expires=0
				)
				
			return {}

		@self.router.post("/register/")
		async def register(
			request: Request,
			response: Response,
			form_data: RouteLogin
		):

			access_token_expires = timedelta(
				minutes=auth_settings.AUTH_ACCESS_TOKEN_EXPIRE_MINUTES
			)

			user_with_username_exists: bool = await check_if_user_exists(
				username=form_data.username
			)

			if user_with_username_exists:
				return {
					"message": "Username or Email already registered."
				}

			if not re.search(password_regex, form_data.password):
				message = 'Password should match the following criteria: <ol><li>At least one uppercase and lowercase letter.</li><li>Minimum eight characters in length.</li><li>At least one digit.</li><li>At least one special character (#?!@$%^&*-).</li></ol>'
				return {
					"message": message
				}

			user: User = await User.create_user(
				username=form_data.username,
				password=form_data.password
			)
			
			access_token, expiry = create_access_token(
				data={"sub": str(user.pk)}, expires_delta=access_token_expires
			)

			await Token.create(
				token=access_token,
				expires=expiry,
				user_id=user.pk,
				secret=AUTH_SECRET_KEY,
				algorithm=AUTH_ALGORITHM
			)

			total_seconds: int = access_token_expires.total_seconds()

			response.set_cookie(
				key="token",
				value=access_token,
				max_age=total_seconds,
				expires=total_seconds
			)

			return await User_Pydantic.from_tortoise_orm(user)

from datetime import (
	datetime,
	timedelta,
	timezone
)
from typing import (
	Optional,
	Union,
	Tuple
)
from fastapi import (
	Depends,
	HTTPException,
	status,
	Request
)

try:
	from tortoise.query_utils import Q
except:
	from tortoise.expressions import Q

from tortoise.timezone import now
from tortoise import models



from jose import (
	JWTError,
	jwt
)
from jose.exceptions import (
	ExpiredSignatureError,
	JWTClaimsError
)
from api_v1.projects.settings import (
	AUTH_SECRET_KEY,
	AUTH_ALGORITHM,
	AUTH_EMAIL_VERIFICATION_EMAIL_BODY
)
from api_v1.projects.models import (
	User,
	Token
)
import api_v1.projects.settings as auth_settings
import api_v1.settings as api_v1_settings
from api_v1.settings import get_settings

import os

environment_vars = get_settings()

async def check_if_user_exists(
	username: str
) -> bool:
	'''
		Checks if a user with the provided username, or email, exists

		params:
			username : str (optional) : the users username
			email : str (optional) : the users email

		returns tuple(bool, bool)
	'''

	email_exists = False
	username_exists = False

	user = await User.filter(
		username=username
	).first()

	if user:

		if user.username == username:
			username_exists = True

	return username_exists

def create_access_token(
	data: dict,
	expires_delta: timedelta | None
) -> tuple[str, datetime]:
	'''
		Creates and returns a new JWT

		params:
			data : str : the data to be encoded in the JWT
			expires_delta : timedelta (optional) : a optional time-delta for when the JWT should expire

		returns tuple(jwt, datetime)
	'''

	to_encode = data.copy()

	if expires_delta:
		expire = now() + expires_delta
	else:
		expire = now() + timedelta(minutes=15)

	to_encode.update({"exp": expire})
	encoded_jwt = jwt.encode(to_encode, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)

	return encoded_jwt, expire

async def get_current_user(
	token
) -> HTTPException | User:
	'''
		Attempts to retrieve the JWT, and extract details - then retrieve a User

		params:
			token : str :the JWT extracted from the Authorization header

		returns User else raises HTTPException
	'''

	exception = HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail="Token expired."
	)

	try:
		token_in_db = await Token.get_or_none(
			token=token
		).only("algorithm", "token", "secret", "force_expiration", "expires")

		if token_in_db is None:
			raise exception

		payload = jwt.decode(token, token_in_db.secret, algorithms=[token_in_db.algorithm])
		pk = payload.get("sub")

		if pk is None or token_in_db.is_expired():
			raise exception
		
	except Exception as e:
		raise exception

	user = await User.get_by_id(id=pk)

	if user is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="User does not exist."
		)

	return user
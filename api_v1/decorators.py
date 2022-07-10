import asyncio
import functools
import inspect
import typing
import re

from starlette.exceptions import HTTPException
from starlette.requests import HTTPConnection, Request
from starlette.responses import RedirectResponse, Response
from starlette.websockets import WebSocket

from fastapi import (
	FastAPI
)
import orjson

from api_v1.settings import get_settings

settings = get_settings()

def requires_login(
	status_code: int = 403
) -> typing.Callable:

	def decorator(func: typing.Callable) -> typing.Callable:

		@functools.wraps(func)
		async def async_wrapper(
			*args: typing.Any,
			**kwargs: typing.Any
		) -> dict | list[dict] | HTTPException:
			request: Request | None = kwargs.get("request", None) ## get the request from the annoteted function

			if not request.user.is_authenticated():
				raise HTTPException(status_code=status_code)

			return await func(*args, **kwargs)

		return async_wrapper

	return decorator

def cache_route(
	app: FastAPI,
	ttl_seconds: int = 15
) -> typing.Callable:

	def decorator(func: typing.Callable) -> typing.Callable:

		@functools.wraps(func)
		async def async_wrapper(
			*args: typing.Any, **kwargs: typing.Any
		) -> dict | list[dict]:
			request: Request | None = kwargs.get("request", None) ## get the request from the annoteted function

			if settings.REDIS_ENABLED:
				cache_key: str = request.url._url

				route_is_cached: bool = bool(await app.state.redis.exists(cache_key))

				if route_is_cached:
					response: dict = orjson.loads(await app.state.redis.get(cache_key))
				else:
					response: list = await func(*args, **kwargs)
					await app.state.redis.set(
						name = cache_key,
						value = orjson.dumps([x.dict() for x in response]),
						ex = ttl_seconds,
						nx = True
					)

				return response

			else:
				return await func(*args, **kwargs)

		return async_wrapper

	return decorator

def delete_cached_route(
	app: FastAPI,
	object_path: str = '',
	related_request_url: str = ''
) -> typing.Callable:

	def decorator(func: typing.Callable) -> typing.Callable:

		@functools.wraps(func)
		async def async_wrapper(
			*args: typing.Any, **kwargs: typing.Any
		) -> dict | list[dict]:
			request: Request = kwargs.get("request", None) ## get the request from the annoteted function
	
			if settings.REDIS_ENABLED:
				cache_key: str = request.url._url
				
				# this lets us de-cache routes which are related to other routes.
				# For example, updating a bug has an impact on the project -msince, the full project is cached
				# As such, we would return stale data if we were to request the project again
				if related_request_url:
					alternate_cache_key = f"{request.url.scheme}://{request.url.netloc}{related_request_url}"
					cache_key: str = alternate_cache_key

				# this lets us have the 'path' to the attribute that we want to append to the url
				# a string with three parts, seperated by fullstops
				# this lets us 'append' additional information to the cache key if we need
				# for example: ?project_id=someID
				if object_path:

					object_name_in_kwargs, object_attr, extra_args = object_path.split('.')

					# get object from kwargs
					object_from_kwargs = kwargs.get(object_name_in_kwargs, None)

					# if we have a object
					if object_from_kwargs:

						# try get the specified attr (for example, 'name', 'id')
						object_attr_from_object = getattr(object_from_kwargs, object_attr, None)
						
						# if this exists..
						if object_attr_from_object:

							# append the additional cache key args to the cache key
							additional_args = f"{extra_args}{object_attr_from_object}"
							cache_key = f"{cache_key}{additional_args}"

				route_is_cached: bool = bool(await app.state.redis.exists(cache_key))

				print(func.__name__)
				print('cache_key = ', cache_key)
				print('route_is_cached = ', route_is_cached)

				if route_is_cached:
					await app.state.redis.delete(cache_key)

			return await func(*args, **kwargs)

		return async_wrapper

	return decorator

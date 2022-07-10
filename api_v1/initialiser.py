from tortoise.contrib.fastapi import register_tortoise
from tortoise import Tortoise
from tortoise.timezone import now
from tortoise.expressions import F
from faker import Faker
from inspect import isfunction

from fastapi import (
	FastAPI,
	Request,
	APIRouter
)
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.authentication import (
	AuthenticationMiddleware
)
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles

import os
import aiojobs
import asyncio
import aioredis
import typing as t
import logging
import time
import uvicorn
import sys

from api_v1.settings import get_settings
from api_v1.projects.models import User
from api_v1.projects import middleware as application_middleware
from api_v1.logging import initialising_logger

environment_vars = get_settings()

DATABASE_NAME = environment_vars.DATABASE_NAME
DATABASE_TORTOISE_BACKEND = environment_vars.DATABASE_TORTOISE_BACKEND
DATABASE_HOST = environment_vars.DATABASE_HOST
DATABASE_PASSWORD = environment_vars.DATABASE_PASSWORD
DATABASE_PORT = environment_vars.DATABASE_PORT
DATABASE_USER = environment_vars.DATABASE_USER
DATABASE_URL = environment_vars.DATABASE_URL
REDIS_URL = environment_vars.REDIS_URL
PREFIX_AND_POSTFIX = "*" * 10

TORTOISE_ORM_CONFIG = {
	'connections':{
		'default': {
			'engine': DATABASE_TORTOISE_BACKEND,
			"use_tz": True,
			"credentials":{
				"database": DATABASE_NAME,
				"host": DATABASE_HOST,
				"password": DATABASE_PASSWORD,
				"port": DATABASE_PORT,
				"user": DATABASE_USER
			}
		}
	},
	"apps": {
		"models":{
			"models": [
				"api_v1.projects.models",
			]
		},
	}
}

def on_auth_error(
	request: Request,
	exc: Exception
):
	return ORJSONResponse({"error": str(exc)}, status_code=401)


def init(
	app: FastAPI
) -> None:

	
	INIT_FUNCS: t.List[t.Callable[FastAPI, None]] = [
		init_db,
		init_services,
		init_middleware
	]

	for func in INIT_FUNCS:
		func(app)

def init_services(
	app: FastAPI
):

	from api_v1.projects.auth_service import AuthService
	from api_v1.projects.project_service import ProjectService

	services: list[Service] = [
		AuthService(
			app = app,
			router_prefix = "/api/v1/auth",
			settings = environment_vars
		),
		ProjectService(
			app = app,
			router_prefix = "/api/v1/projects",
			settings = environment_vars
		)
	]

	initialising_logger.info('Intalling...')

	for idx, service in enumerate(services):
		service.install()
		service.install_router()
		initialising_logger.info('{}. Installed {}...'.format(idx, service))

	initialising_logger.info('Finished...')

def init_middleware(
	app: FastAPI
) -> None:

	initialising_logger.info('Installing AuthenticationMiddleware...')

	app.add_middleware(
		AuthenticationMiddleware,
		backend=application_middleware.JWTCookieAuthBackend(),
		on_error=on_auth_error
	)

	initialising_logger.info('Finished installing AuthenticationMiddleware...')

	CORS_ORIGINS: list[str] = []
	for port in range(0, 65535):
		CORS_ORIGINS.extend([
			f"{environment_vars.FRONTEND_ADDRESS}",
			f"http://localhost:{port}",
			f"http://127.0.0.1:{port}"
		])
		
	## be able to specify the environment vars
	ENV_ORIGINS = environment_vars.ENV_ORIGINS

	if ENV_ORIGINS:
		ENV_ORIGINS: list[str] = ENV_ORIGINS.split(',')
		CORS_ORIGINS.extend(ENV_ORIGINS)

	initialising_logger.info('Installing CORSMiddleware...')

	app.add_middleware(
		CORSMiddleware,
		allow_origins=CORS_ORIGINS,
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
		expose_headers=['X-Process-Time', 'X-Route-Name']
	)

	initialising_logger.info('Finished installing CORSMiddleware...')

	if environment_vars.STORAGE_ENABLED:
		initialising_logger.info('Mounting StaticFiles...')
		app.mount(
			"/public",
			StaticFiles(
				directory=environment_vars.DOCUMENT_DIRECTORY
			),
			name="public"
		)
		initialising_logger.info('Finished mounting StaticFiles...')

	@app.on_event("startup")
	async def startup():

		if environment_vars.REDIS_ENABLED:
			app.state.redis = aioredis.from_url(REDIS_URL, decode_responses=True)
		else:
			app.state.redis = None

	@app.on_event("shutdown")
	async def shutdown():

		if environment_vars.REDIS_ENABLED:
			await app.state.redis.close()


def init_db(
	app: FastAPI
) -> None:

	initialising_logger.info('Installing Tortoise-ORM...')
	register_tortoise(
		app=app,
		config=TORTOISE_ORM_CONFIG,
		generate_schemas=True
	)
	initialising_logger.info('Finished installing Tortoise-ORM...')

def format_loggers(
	formatter
):

	root_logger = logging.getLogger()
	root_logger.setLevel(logging.INFO)

	info_stream_handler = logging.StreamHandler()
	info_stream_handler.setLevel(logging.INFO)
	info_stream_handler.setFormatter(formatter)

	# Remove ALL of the loggers
	for handler in root_logger.handlers:
		root_logger.removeHandler(handler)

	# add ch to logger
	root_logger.addHandler(info_stream_handler)

	# logger_db_client = logging.getLogger("db_client")
	# logger_db_client.setLevel(logging.INFO)

	# for handler in logger_db_client.handlers:
	# 	logger_db_client.removeHandler(handler)

	# logger_db_client.addHandler(info_stream_handler)

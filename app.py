import argparse
import sys
import os
import logging
from uvicorn import run, logging as uvicorn_logging
import time

from fastapi import (
	FastAPI,
	Request,
	BackgroundTasks,
	APIRouter
)
from fastapi.responses import ORJSONResponse

from api_v1.initialiser import init, format_loggers
from api_v1.settings import get_settings

console_formatter = uvicorn_logging.ColourizedFormatter(
	fmt="%(levelprefix)s %(asctime)s - %(name)s:%(funcName)s:%(lineno)d - %(message)s",
	datefmt="%Y-%m-%d %H:%M:%S",
	use_colors=True
)

app: FastAPI = FastAPI(
	title='FastAPI Application',
	version='1.0',
	docs_url=None,
	redoc_url=None,
	debug=False,
	default_response_class=ORJSONResponse
)
environment_vars = get_settings()

format_loggers(
	formatter=console_formatter
)

if __name__ == "__main__":
	run(
		app="app:app",
		host=environment_vars.FRONTEND_ADDRESS,
		log_config=None,
		use_colors=True
	)
else:
	init(app)

@app.middleware("http")
async def add_process_time_header(request, call_next):
	request_path = request.scope['path']
	start_time = time.perf_counter()
	response = await call_next(request)
	response.headers["X-Route-Name"] = next((x.name for x in request.app.router.routes if x.path.startswith(request_path)), '')
	response.headers["X-Process-Time"] = str(time.perf_counter() - start_time)

	return response
from typing import List

from fastapi import (
	APIRouter,
    FastAPI
)
from api_v1.settings import (
    Settings,
    get_settings
)

class Service:

    __slots__ = (
        'app',
        'router_prefix',
        'router',
        'settings',
        'sub_services',
    )

    def __init__(
        self: 'Service',
        app: FastAPI,
        router_prefix: str = '/',
        settings: Settings = None
    ):  

        self.app: FastAPI = app
        self.router_prefix: str = router_prefix
        self.router: APIRouter = APIRouter()
        self.settings: Settings = settings or get_settings()
        self.sub_services: list['Service'] = []

    def install(
        self: 'Service'
    ):
        ...

    def install_router(
        self: 'Service'
    ):

        for sub_service in self.sub_services:
            sub_service.install()
            self.router.include_router(
                router = sub_service.router
            )

        self.app.include_router(
            router = self.router,
            prefix = self.router_prefix
        )


    def __str__(
        self: 'Service'
    ) -> str:
        return self.__class__.__name__
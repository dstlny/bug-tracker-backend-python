from pydantic import BaseModel
from typing import (
	Optional,
	Union,
	Literal,
	List
)

from api_v1.projects.enums import (
    StatusEnum,
    PriorityEnum,
	ObjectEnum,
	ColorEnum
)

class RouteLogin(BaseModel):

	username: str | None
	password: str | None

class RouteBug(BaseModel):
	
	id: int | None
	content: str
	status: StatusEnum = StatusEnum.OPEN
	priority: PriorityEnum = PriorityEnum.HIGH
	project_id: int
	allocated_to_ids: list[int] | None
	badge_ids: list[int] | None

class RouteProject(BaseModel):
	
	id: int | None
	name: str
	status: StatusEnum = StatusEnum.OPEN
	priority: PriorityEnum = PriorityEnum.HIGH
	client_id: int
	badge_ids: list[int] | None
class RouteClient(BaseModel):

	id: int | None
	name: str
	is_internal: bool

class RouteComment(BaseModel):

	content: str
	project_id: int | None
	bug_id: int | None

class InIDS(BaseModel):

	ids: list[int]

class InAuditTrails(BaseModel):

	object_class: str
	object_id: int

class RouteThread(BaseModel):

	thread_id: int

class RouteThreadReply(RouteThread):

	thread_id: int
	content: str

class RouteBadge(BaseModel):
	
	object_id: int
	object_type: ObjectEnum = ObjectEnum.PROJECT
	label: str
	color: ColorEnum = ColorEnum.RED
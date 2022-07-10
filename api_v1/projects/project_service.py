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
	Query,
	File,
	UploadFile
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
from tortoise.functions import Count
from sse_starlette.sse import EventSourceResponse

from datetime import timedelta
import re
import typing
import json
import asyncio 
from dateutil import parser
import bleach
import os
import orjson

import api_v1.projects.settings as auth_settings
from api_v1.projects.functions import *
from api_v1.projects.route_models import *
from api_v1.projects.models import (
	Token,
	User,
	Project,
	Bug,
	Organisation,
	Comment,
	ObjectHistory,
	Thread,
	ThreadReply,
	Badge,
	Document
)
from api_v1.projects.settings import (
	AUTH_SECRET_KEY,
	AUTH_ALGORITHM
)
from api_v1.decorators import (
	requires_login,
	cache_route,
	delete_cached_route
)
from api_v1.settings import get_settings
from api_v1.base_service import Service
from api_v1.pydantic.models import (
	Bug_Pydantic,
	Project_Pydantic,
	Organisation_Pydantic,
	ProjectListing_Pydantic,
	ObjectHistory_Pydantic,
	CommentListing_Pydantic,
	ThreadListing_Pydantic,
	ThreadReplyListing_Pydantic,
	Badge_Pydantic
)
from api_v1.projects.enums import (
	StatusEnum,
	PriorityEnum,
	ObjectEnum,
	DocumentCategoryEnum
)
from typing import (
	Optional
)

class ProjectService(Service):

	def install(self):
		




		##################################### 
		# project related endpoints
		##################################### 
		@self.router.get('/')
		@cache_route(
			app = self.app
		)
		async def get_projects(
			request: Request,
			project_id: Optional[int] = None,
			client_id: Optional[int] = None
		) -> Project_Pydantic | ProjectListing_Pydantic:

			if project_id:
				return await Project_Pydantic.from_queryset(
					queryset = Project.filter(id = project_id)
				)

			if client_id:
				return await ProjectListing_Pydantic.from_queryset(
					queryset = Project.filter(
						client_id = client_id
					).annotate(
						b_count = Count('bugs')
					)
				)
		
			return await ProjectListing_Pydantic.from_queryset(
				queryset = Project.all().annotate(
					b_count = Count('bugs'),
					c_count = Count('comments')
				)
			)

		@self.router.delete('/')
		@delete_cached_route(
			app = self.app
		)
		async def delete_projects(
			request: Request,
			in_ids: InIDS
		) -> dict:

			await Project.filter(id__in = in_ids.ids).delete()
			return {}

		@self.router.post('/')
		@requires_login(status_code = 403)
		@delete_cached_route(
			app = self.app,
			object_path = 'project_data.id.?project_id='
		)
		async def create_or_update_project(
			request: Request,
			project_data: RouteProject
		) -> Project_Pydantic:

			if project_data.id:

				project: Project = await Project.get(
					pk = project_data.id
				)

				update_fields: List[str] = []
				object_histories: List[ObjectHistory] = []

				if project.name != project_data.name:
					
					object_histories.append(ObjectHistory(
						object_class = project.__class__.__name__,
						object_id = project.pk,

						attribute_name = 'name',
						attribute_type = str(project.name.__class__.__name__),
						attribute_prior_state = project.name,
						attribute_new_state = project_data.name
					))

					project.name = project_data.name
					update_fields.append('name')
		
				if project.status != project_data.status:

					object_histories.append(ObjectHistory(
						object_class = project.__class__.__name__,
						object_id = project.pk,

						attribute_name = 'status',
						attribute_type = str(project.status.__class__.__name__),
						attribute_prior_state = project.status.value,
						attribute_new_state = project_data.status.value
					))

					project.status = project_data.status
					update_fields.append('status')

				if project.priority != project_data.priority:

					object_histories.append(ObjectHistory(
						object_class = project.__class__.__name__,
						object_id = project.pk,
	
						attribute_name = 'priority',
						attribute_type = str(project.priority.__class__.__name__),
						attribute_prior_state = project.priority.value,
						attribute_new_state = project_data.priority.value
					))

					project.priority = project_data.priority
					update_fields.append('priority')

				if project.client_id != project_data.client_id:

					new_client = await Organisation.get(pk = project_data.client_id)
					old_client = await project.client

					object_histories.append(ObjectHistory(
						object_class = project.__class__.__name__,
						object_id = project.pk,

						attribute_name = 'client',
						attribute_type = str(old_client.__class__.__name__),
						attribute_prior_state = old_client.name,
						attribute_new_state = new_client.name
					))

					project.client = new_client
					update_fields.append('client_id')

				if project_data.badge_ids:
					
					# get a set of current and proposed ids
					current_ids: set[int] = set(await project.badges.all().values_list('id', flat = True))
					proposed_ids: set[int] = set(project_data.badge_ids)

					if current_ids != proposed_ids:
						
						# get all proposed and currently allocated badges
						proposed_badges: list[Badge] = await Badge.filter(id__in = proposed_ids)
						current_badges: list[Badge]  = await Badge.filter(id__in = current_ids)

						# get all proposed and currently allocated badge labels
						proposed_labels: list[str] = [x.label for x in proposed_badges]
						current_labels: list[str] = [x.label for x in current_badges]

						# do we have some current badges and proposed badges?
						if current_labels and proposed_labels:

							# record this in history
							object_histories.append(ObjectHistory(
								object_class = project.__class__.__name__,
								object_id = project.pk,

								attribute_name = 'badges',
								attribute_type = str(project.badges.__class__.__name__),
								attribute_prior_state = ', '.join(current_labels) or 'No badges',
								attribute_new_state = ', '.join(proposed_labels)
							))

						# do we not have any current, but some proposed badges?
						elif not current_labels and proposed_labels:

							# record this in history
							object_histories.append(ObjectHistory(
								object_class = project.__class__.__name__,
								object_id = project.pk,

								attribute_name = 'badges',
								attribute_type = str(project.badges.__class__.__name__),
								attribute_prior_state = 'No badges',
								attribute_new_state = ', '.join(proposed_labels)
							))

						# clear anyone currently allocated to the bug..
						await project.badges.clear()

						# add the people that have been proposed to be allocated
						await project.badges.add(*proposed_badges)

				else:

					# get the current usernames of users allocated
					current_badges: set[str] = set(await project.badges.all().values_list('label', flat = True))

					# clear the current users allocated
					await project.badges.clear()

					# create a history of the object
					object_histories.append(ObjectHistory(
						object_class = project.__class__.__name__,
						object_id = project.pk,

						attribute_name = 'badges',
						attribute_type = str(project.badges.__class__.__name__),
						attribute_prior_state = ', '.join(current_badges),
						attribute_new_state = 'no badges'
					))


				await ObjectHistory.bulk_create(object_histories)
   
				await project.save(
					update_fields=update_fields
				)
			else:

				project = await Project.create(
					name = project_data.name,
					status = project_data.status,
					priority = project_data.priority,
					author = request.user,
					client_id = project_data.client_id
				)
	
			return await Project_Pydantic.from_queryset(
				queryset = Project.filter(id = project.pk).annotate(
					b_count = Count('bugs'),
					c_count = Count('comments')
				)
			)





		##################################### 
		# badge related endpoints
		##################################### 
		@self.router.get('/badges/')
		async def get_badges(
			request: Request
		) -> Badge_Pydantic:

			return await Badge_Pydantic.from_queryset(
				queryset = Badge.all()
			)


		@self.router.post('/badges/')
		@requires_login(status_code = 403)
		@delete_cached_route(
			app = self.app
		)
		async def create_or_update_badge(
			request: Request,
			badge_data: RouteBadge
		) -> Badge_Pydantic:

			badge, existing = await Badge.get_or_create(
				label = badge_data.label,
				color = badge_data.color
			)

			if badge_data.object_type is ObjectEnum.PROJECT:
				
				project = await Project.get(id = badge_data.object_id)
				await project.badges.add(*[badge])

			elif badge_data.object_type is ObjectEnum.BUG:

				bug = await Bug.get(id = badge_data.object_id)
				await bug.badges.add(*[badge])

			return await Badge_Pydantic.from_queryset(
				queryset = Badge.filter(id = badge.id)
			)





		##################################### 
		# bug related endpoints
		##################################### 
		@self.router.get('/client/')
		async def get_clients(
			request: Request,
			client_id: Optional[int] = None
		) -> Organisation_Pydantic:

			if client_id:
				return await Organisation_Pydantic.from_queryset(
					queryset = Organisation.filter(id = client_id)
				)

			return await Organisation_Pydantic.from_queryset(
				queryset = Organisation.all()
			)

		@self.router.delete('/clients/')
		@delete_cached_route(
			app = self.app
		)
		async def delete_organisations(
			request: Request,
			in_ids: InIDS
		) -> dict:

			await Organisation().filter(id__in = in_ids.ids).delete()
			return {}

		@self.router.post('/client/')
		@requires_login(status_code = 403)
		async def create_or_update_client(
			request: Request,
			client_data: RouteClient
		) -> Organisation_Pydantic:  


			if client_data.id:

				client: Organisation = await Organisation.get(
					pk = client_data.id
				)

				update_fields: list[str] = []
				object_histories: list[ObjectHistory] = []

				# are the names the same?
				if client.name != client_data.name:
					
					# record this in history
					object_histories.append(ObjectHistory(
						object_class = client.__class__.__name__,
						object_id = client.pk,

						attribute_name = 'name',
						attribute_type = str(type(client.name)),
						attribute_prior_state = client.name,
						attribute_new_state = client_data.name
					))

					client.name = client_data.name
					update_fields.append('name')

				# is the is_internal flag the same?
				if client.is_internal != client_data.is_internal:
					
					# record this in history
					object_histories.append(ObjectHistory(
						object_class = client.__class__.__name__,
						object_id = client.pk,
	
						attribute_name = 'is_internal',
						attribute_type = str(type(client.is_internal)),
						attribute_prior_state = str(client.is_internal),
						attribute_new_state = str(client_data.is_internal)
					))

					client.is_internal = client_data.is_internal
					update_fields.append('is_internal')
					

				await ObjectHistory.bulk_create(object_histories)
   
				await client.save(
					update_fields=update_fields
				)

			else:

				client, created = await Organisation.get_or_create(
					name = client_data.name,
					is_internal = client_data.is_internal
				)

			return await Organisation_Pydantic.from_tortoise_orm(
				obj = client
			)





		##################################### 
		# bug related endpoints
		##################################### 
		@self.router.get('/audit_trails/')
		async def get_audit_trails(
			request: Request,
			object_class: str,
			object_id: int
		) -> ObjectHistory_Pydantic:

			if object_class.lower() == 'all':
				return await ObjectHistory_Pydantic.from_queryset(
					queryset = ObjectHistory.all()
				)

			return await ObjectHistory_Pydantic.from_queryset(
				queryset = ObjectHistory.filter(
					object_class = object_class,
					object_id = object_id
				)
			)





		##################################### 
		# bug related endpoints
		##################################### 
		@self.router.delete('/bug/')
		@delete_cached_route(
			app = self.app
		)
		async def bulk_close_bugs(
			request: Request,
			in_ids: InIDS
		) -> dict:

			await Bug.filter(
				id__in = in_ids.ids,
				status=StatusEnum.OPEN
			).update(
				status=StatusEnum.CLOSED
			)

			all_history: list[ObjectHistory] = [
				ObjectHistory(
					object_class = 'Bug',
					object_id = pk,

					attribute_name = 'status',
					attribute_type ='StatusEnum',
					attribute_prior_state = 'Open',
					attribute_new_state = 'Closed'
				)
				for pk in in_ids.ids
			]
			await ObjectHistory.bulk_create(objects=all_history)
			return {}

		@self.router.post('/bug/')
		@requires_login(status_code = 403)
		@delete_cached_route(
			app = self.app,
			object_path = 'bug_data.project_id.?project_id=',
			related_request_url='/api/v1/projects/'
		)
		async def create_or_update_bug(
			request: Request,
			bug_data: RouteBug
		) -> Bug_Pydantic:

			
			project: Project | None = await Project.get_or_none(pk = bug_data.project_id)

			if bug_data.id:

				bug: Bug = await Bug.get(id = bug_data.id)
	
				update_fields: list[str] = []
				object_histories: list[ObjectHistory] = []
				
				# are the contents different?
				if bug.content != bug_data.content:
					
					# record this in history
					object_histories.append(ObjectHistory(
						object_class = bug.__class__.__name__,
						object_id = bug.pk,

						attribute_name = 'content',
						attribute_type = str(bug.content.__class__.__name__),
						attribute_prior_state = bug.content,
						attribute_new_state = bug_data.content
					))

					bug.content = bug_data.content
					update_fields.append('content')
				
				# are the statuses different?
				if bug.status != bug_data.status:

					# record this in history
					object_histories.append(ObjectHistory(
						object_class = bug.__class__.__name__,
						object_id = bug.pk,

						attribute_name = 'status',
						attribute_type = str(bug.status.__class__.__name__),
						attribute_prior_state = bug.status.value,
						attribute_new_state = bug_data.status.value
					))

					bug.status = bug_data.status
					update_fields.append('status')

				# are the priorities different?
				if bug.priority != bug_data.priority:

					# record this in history
					object_histories.append(ObjectHistory(
						object_class = bug.__class__.__name__,
						object_id = bug.pk,

						attribute_name = 'priority',
						attribute_type = str(bug.priority.__class__.__name__),
						attribute_prior_state = bug.priority.value,
						attribute_new_state = bug_data.priority.value
					))

					bug.priority = bug_data.priority
					update_fields.append('priority')

				if bug_data.allocated_to_ids:

					# get a list of current usernames and ids of those allocated to this bug
					current_data: list[dict[str, int]] = await bug.allocated_to.all().values('username', 'id')

					# get a set of current and proposed ids
					current_ids: set[int] = set([x['id'] for x in current_data])
					proposed_ids: set[int] = set(bug_data.allocated_to_ids)

					if current_ids != proposed_ids:
						
						# get all proposed and currently allocated users
						proposed_users: list[User] = await User.filter(id__in = proposed_ids)
						current_users: list[User]  = await User.filter(id__in = current_ids)

						# get all proposed and currently allocated user usernames
						proposed_usernames: list[str] = [x.username for x in proposed_users]
						current_usernames: list[str] = [x.username for x in current_users]

						# do we have some current usernames and proposed usernames?
						if current_usernames and proposed_usernames:

							# record this in history
							object_histories.append(ObjectHistory(
								object_class = bug.__class__.__name__,
								object_id = bug.pk,

								attribute_name = 'allocated_to',
								attribute_type = str(bug.allocated_to.__class__.__name__),
								attribute_prior_state = ', '.join(current_usernames) or 'Nobody',
								attribute_new_state = ', '.join(proposed_usernames)
							))

						# do we not have any current, but some proposed users?
						elif not current_usernames and proposed_usernames:

							# record this in history
							object_histories.append(ObjectHistory(
								object_class = bug.__class__.__name__,
								object_id = bug.pk,
	
								attribute_name = 'allocated_to',
								attribute_type = str(bug.allocated_to.__class__.__name__),
								attribute_prior_state = 'Nobody',
								attribute_new_state = ', '.join(proposed_usernames)
							))

						# clear anyone currently allocated to the bug..
						await bug.allocated_to.clear()

						# add the people that have been proposed to be allocated
						await bug.allocated_to.add(*proposed_users)

				else:

					# get the current usernames of users allocated
					current_usernames: set[str] = set(await bug.allocated_to.all().values_list('username', flat = True))

					# clear the current users allocated
					await bug.allocated_to.clear()

					# create a history of the object
					object_histories.append(ObjectHistory(
						object_class = bug.__class__.__name__,
						object_id = bug.pk,

						attribute_name = 'allocated_to',
						attribute_type = str(bug.allocated_to.__class__.__name__),
						attribute_prior_state = ', '.join(current_usernames),
						attribute_new_state = 'nobody'
					))

				print(bug_data.badge_ids)
				if bug_data.badge_ids:
					
					# get a set of current and proposed ids
					current_ids: set[int] = set(await bug.badges.all().values_list('id', flat = True))
					proposed_ids: set[int] = set(bug_data.badge_ids)

					if current_ids != proposed_ids:
						
						# get all proposed and currently allocated badges
						proposed_badges: list[Badge] = await Badge.filter(id__in = proposed_ids)
						current_badges: list[Badge]  = await Badge.filter(id__in = current_ids)

						# get all proposed and currently allocated badge labels
						proposed_labels: list[str] = [x.label for x in proposed_badges]
						current_labels: list[str] = [x.label for x in current_badges]

						# do we have some current badges and proposed badges?
						if current_labels and proposed_labels:

							# record this in history
							object_histories.append(ObjectHistory(
								object_class = bug.__class__.__name__,
								object_id = bug.pk,

								attribute_name = 'badges',
								attribute_type = str(bug.badges.__class__.__name__),
								attribute_prior_state = ', '.join(current_labels) or 'No badges',
								attribute_new_state = ', '.join(proposed_labels)
							))

						# do we not have any current, but some proposed badges?
						elif not current_labels and proposed_labels:

							# record this in history
							object_histories.append(ObjectHistory(
								object_class = bug.__class__.__name__,
								object_id = bug.pk,

								attribute_name = 'badges',
								attribute_type = str(bug.badges.__class__.__name__),
								attribute_prior_state = 'No badges',
								attribute_new_state = ', '.join(proposed_labels)
							))

						# clear anyone currently allocated to the bug..
						await bug.badges.clear()

						# add the people that have been proposed to be allocated
						await bug.badges.add(*proposed_badges)

				else:

					# get the current usernames of users allocated
					current_badges: set[str] = set(await bug.badges.all().values_list('label', flat = True))

					# clear the current users allocated
					await bug.badges.clear()

					# create a history of the object
					object_histories.append(ObjectHistory(
						object_class = bug.__class__.__name__,
						object_id = bug.pk,

						attribute_name = 'badges',
						attribute_type = str(bug.badges.__class__.__name__),
						attribute_prior_state = ', '.join(current_badges),
						attribute_new_state = 'no badges'
					))

				await ObjectHistory.bulk_create(object_histories)
   
				await bug.save(
					update_fields=update_fields
				)

			else:
				bug = await Bug.create(
					content = bug_data.content,
					status = bug_data.status,
					priority = bug_data.priority,
					owner = request.user,
					project = project
				)

				# get a set of ids of those proposed
				proposed_ids: set[int] = set(bug_data.allocated_to_ids)

				# get the users who are proposed
				proposed_users: list[User] = await User.filter(id__in = proposed_ids)

				# allocate those that are proporsed to the bug
				await bug.allocated_to.add(*proposed_users)

			return await Bug_Pydantic.from_tortoise_orm(
				obj = bug
			)
		
		@self.router.get('/bug/comments/')
		async def get_bug_comments(
			request: Request,
			bug_id: Optional[int]
		) -> CommentListing_Pydantic:

			return await CommentListing_Pydantic.from_queryset(
				queryset = Comment.filter(bug_id = bug_id)
			)

		@self.router.get('/bug/threads/')
		async def get_bug_threads(
			request: Request,
			bug_id: Optional[int]
		) -> ThreadListing_Pydantic:

			return await ThreadListing_Pydantic.from_queryset(
				queryset = Thread.filter(bug_id = bug_id)
			)





		##################################### 
		# bug related endpoints
		#####################################  
		@self.router.post('/comments/')
		@requires_login(status_code = 403)
		async def create_comment(
			request: Request,
			comment_data: RouteComment
		) -> ProjectListing_Pydantic:

			if comment_data.bug_id:
				await Comment.create(
					content = comment_data.content,
					author = request.user,
					bug_id = comment_data.bug_id
				)
			else:
				await Comment.create(
					content = comment_data.content,
					author = request.user,
					project_id = comment_data.project_id
				)

			return {}





		##################################### 
		# thread related endpoints
		##################################### 
		@self.router.get('/threads/replies/')
		async def get_thread_replies(
			request: Request,
			thread_id: Optional[int]
		) -> ThreadReplyListing_Pydantic:

			return await ThreadReplyListing_Pydantic.from_queryset(
				queryset = ThreadReply.filter(thread_id = thread_id)
			)

		@self.router.post('/threads/replies/')
		@requires_login(status_code = 403)
		async def create_thread_reply(
			request: Request,
			thread_reply_data: RouteThreadReply
		) -> ThreadReplyListing_Pydantic:

			await ThreadReply.create(
				content = thread_reply_data.content,
				author = request.user,
				thread_id = thread_reply_data.thread_id
			)

			return await ThreadReplyListing_Pydantic.from_queryset(
				queryset = ThreadReply.filter(thread_id = thread_reply_data.thread_id)
			)

		@self.router.post('/threads/')
		@requires_login(status_code = 403)
		async def create_thread(
			request: Request,
			thread_data: RouteComment
		) -> ProjectListing_Pydantic:

			if thread_data.bug_id:
				await Thread.create(
					content = thread_data.content,
					author = request.user,
					bug_id = thread_data.bug_id
				)
			else:
				await Thread.create(
					content = thread_data.content,
					author = request.user,
					project_id = thread_data.project_id
				)

			return {}
			




		##################################### 
		# thread related endpoints
		#####################################
		@self.router.post('/documents/upload/')
		@requires_login(status_code = 403)
		async def upload_documents(
			request: Request,
			document_to_upload: UploadFile = File(...),
			category: DocumentCategoryEnum = DocumentCategoryEnum.PROJECT,
			category_id: int = 0
		) -> None:

			document = await Document.handle_upload(
				file_to_upload = document_to_upload,
				category = category
			)

			if category is DocumentCategoryEnum.PROJECT:

				project = await Project.get(id = category_id)
				await project.documents.add(document)

			else:

				bug = await Bug.get(id = category_id)
				await bug.documents.add(document)

			return {}
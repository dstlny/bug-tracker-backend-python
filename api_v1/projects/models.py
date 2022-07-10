from tortoise import models, fields, Tortoise
from tortoise.timezone import now
from tortoise.signals import post_save
from tortoise.manager import Manager
from tortoise.query_utils import Prefetch
from tortoise.expressions import F

from fastapi import status, HTTPException, UploadFile

import asyncio
import orjson
import aiofiles
import os
import uuid
from passlib.context import CryptContext
from datetime import datetime
from pathlib import Path

from api_v1.projects.enums import (
	StatusEnum,
	PriorityEnum,
	ColorEnum,
	DocumentCategoryEnum
)

from api_v1.settings import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AbstractDateCreatedAndUpdated(models.Model):

	date_created: datetime = fields.DatetimeField(
		auto_now_add = True
	)

	date_updated: datetime = fields.DatetimeField(
		auto_now = True
	)

	class Meta:
		abstract = True


######################################################
# Tortoise Models
######################################################
class User(models.Model):

	''' 
		This defines a user
	'''

	username: str = fields.CharField(
		max_length=225
	)

	password: str = fields.CharField(
		max_length=225
	)
	
	bugs: fields.ReverseRelation['Bug']

	comments: fields.ReverseRelation['Comment']

	projects: fields.ReverseRelation['Project']

	threadreplys: fields.ReverseRelation['ThreadReply']

	user_allocated_bugs: fields.ReverseRelation['Bug']

	@classmethod
	def _get_password_context(cls: 'User') -> CryptContext:
		return pwd_context

	@classmethod
	def _create_password(cls: 'User', password: str	) -> str:
		return pwd_context.hash(password)

	create_password = _create_password

	@classmethod
	def _verify_password(cls: 'User', plain_password: str, hashed_password: str) -> bool:
		return pwd_context.verify(plain_password, hashed_password)

	verify_password = _verify_password

	@classmethod
	async def _get_by_username(cls: 'User', username: str) -> "User | None":
		return await cls.get_or_none(username=username)

	get_by_username = _get_by_username

	@classmethod
	async def _get_by_id(cls: 'User', id: int) -> "User | None":
		return await cls.get_or_none(pk=id)

	get_by_id = _get_by_id

	@classmethod
	async def _create_user(cls: 'User', **kwargs) -> "User":
		kwargs['password']: str = cls.create_password(kwargs['password'])
		return await cls.create(**kwargs)

	create_user = _create_user

	@classmethod
	async def _authenticate_user(
		cls,
		username: str,
		password: str
	) -> "User | HTTPException":
		'''
			Tries to authenticate a user

			params:
				username : str : the users username
				password : str : the users plain-text password
				email : str (optional) : the users email

			returns User else raises
		'''

		user: User = await User.get_by_username(
			username=username
		)

		if user is None:
			User._get_password_context().dummy_verify()  # Prevent Timing Attacks
			raise HTTPException(
				status_code=status.HTTP_401_UNAUTHORIZED,
				detail=f"User with username '{username}' does not exist.",
				headers={"WWW-Authenticate": "Bearer"}
			)

		if not User.verify_password(
			plain_password=password,
			hashed_password=user.password
		):
			raise HTTPException(
				status_code=status.HTTP_401_UNAUTHORIZED,
				detail="Incorrect username or password.",
				headers={"WWW-Authenticate": "Bearer"}
			)

		return user

	authenticate_user = _authenticate_user

	def __str__(self: 'User') -> str:
		return "{} ({})".format(self.uuid, self.username)

	def is_authenticated(self: 'User') -> bool:
		if self.pk:
			return True
		else:
			return False

	def display_name(self: 'User') -> str:
		return self.username

class Token(models.Model):
	
	''' 
		This defines a JWT Token
	'''

	token: str= fields.CharField(
		max_length=225
	)
	user_id: str = fields.CharField(
		max_length=225
	)
	algorithm: str = fields.TextField()
	secret: str = fields.TextField()
	expires: datetime = fields.DatetimeField()
	force_expiration: bool = fields.BooleanField(
		default=False
	)
	is_refresh: bool = fields.BooleanField(
		default=False
	)

	def __str__(self: 'Token') -> str:
		return "{} ({})".format(self.id, self.token)

	def is_expired(self: 'Token') -> bool:
		return self.expires < now()

class Project(AbstractDateCreatedAndUpdated):

	name: str = fields.CharField(
		max_length=225
	)

	status: StatusEnum = fields.CharEnumField(
		enum_type=StatusEnum,
		default=StatusEnum.OPEN
	)

	priority: PriorityEnum = fields.CharEnumField(
		enum_type=PriorityEnum,
		default=PriorityEnum.HIGH
	)

	author: fields.ForeignKeyRelation[User] = fields.ForeignKeyField('models.User')
	
	client: fields.ForeignKeyRelation['Organisation'] = fields.ForeignKeyField('models.Organisation')

	bugs: fields.ReverseRelation['Bug']

	comments: fields.ReverseRelation['Comment']

	threads: fields.ReverseRelation['Thread']

	threadreplys: fields.ReverseRelation['ThreadReply']

	badges: fields.ManyToManyRelation['Badge'] = fields.ManyToManyField('models.Badge', related_name='project_badges')

	documents: fields.ManyToManyRelation['Document'] = fields.ManyToManyField('models.Document', related_name='project_documents')

	# count of comments - small optimisation
	def comment_count(self: 'Project') -> int:
		
		if hasattr(self, 'c_count'):
			return self.c_count

		return 0

	# count of bugs - small optimisation
	def bug_count(self: 'Project') -> int:
		
		if hasattr(self, 'b_count'):
			return self.b_count

		return 0


class Bug(AbstractDateCreatedAndUpdated):

	content: str = fields.TextField()

	status: StatusEnum = fields.CharEnumField(
		enum_type=StatusEnum,
		default=StatusEnum.OPEN
	)

	priority: PriorityEnum = fields.CharEnumField(
		enum_type=PriorityEnum,
		default=PriorityEnum.HIGH
	)

	owner: fields.ForeignKeyRelation[User]  = fields.ForeignKeyField('models.User')

	allocated_to: fields.ManyToManyRelation[User] = fields.ManyToManyField('models.User', related_name='user_allocated_bugs')

	project: fields.ForeignKeyRelation[Project] = fields.ForeignKeyField('models.Project')

	badges: fields.ManyToManyRelation['Badge'] = fields.ManyToManyField('models.Badge', related_name='bug_badges')

	documents: fields.ManyToManyRelation['Document'] = fields.ManyToManyField('models.Document', related_name='bug_documents')

class Comment(AbstractDateCreatedAndUpdated):

	content: str = fields.TextField()

	author: fields.ForeignKeyRelation[User] = fields.ForeignKeyField('models.User')

	project: fields.ForeignKeyRelation[Project] = fields.ForeignKeyField('models.Project', null=True)

	bug: fields.ForeignKeyRelation[Bug] = fields.ForeignKeyField('models.Bug', null=True)


class Thread(Comment):
	...

class ThreadReply(Comment):

	thread: fields.ForeignKeyRelation[Thread] = fields.ForeignKeyField('models.Thread')

class Organisation(models.Model):

	name: str = fields.CharField(
		max_length=225
	)

	is_internal: bool = fields.BooleanField(default = False)

class ObjectHistory(AbstractDateCreatedAndUpdated):

	object_class: str = fields.CharField(
		max_length=225
	)

	object_id: int = fields.IntField()

	attribute_name: str = fields.CharField(
		max_length=225
	)

	attribute_type: str  = fields.CharField(
		max_length=225
	)

	attribute_prior_state: str = fields.CharField(
		max_length=225
	)

	attribute_new_state: str  = fields.CharField(
		max_length=225
	)

	def object_comment(self) -> str:
		return f"{self.attribute_name.replace('_',' ').title()} changed from '{self.attribute_prior_state}' to '{self.attribute_new_state}'"

class Badge(models.Model):

	label: str = fields.CharField(
		max_length=225
	)

	color: ColorEnum = fields.CharEnumField(
		enum_type=ColorEnum,
		default=ColorEnum.BLUE
	)


class Document(models.Model):

	CHUNK_SIZE = 2 ** 20  # 1MB

	name: str = fields.CharField(max_length=225)

	original_name: str = fields.CharField(max_length=225)

	category: DocumentCategoryEnum = fields.CharEnumField(
		enum_type=DocumentCategoryEnum,
		default=DocumentCategoryEnum.PROJECT
	)

	path: str = fields.CharField(max_length=225)

	def __str__(self) -> str:
		return f"{self.name}"
	
	def public_path(self) -> str:
		return f"/public/{self.category.value}/{self.name}"

	@classmethod
	async def handle_upload(
		cls,
		file_to_upload: UploadFile,
		category: DocumentCategoryEnum
	) -> None:

		environment_vars = get_settings()

		filename = file_to_upload.filename
		original_name, extension = os.path.splitext(filename)
		new_file_name = uuid.uuid4()
		original_filename = f'{original_name}{extension}'
		new_filename = f"{new_file_name}{extension}"
		subdir = environment_vars.DOCUMENT_DIRECTORY / category.value
		new_path = (environment_vars.DOCUMENT_DIRECTORY / str(category.value).lower() / new_filename).resolve()

		## only if sotrage is enabled
		if environment_vars.STORAGE_ENABLED:

			if not subdir.exists():
				subdir.mkdir()

			# write the file
			await file_to_upload.seek(0)
			async with aiofiles.open(new_path, 'wb+') as out_file:
				while content := await file_to_upload.read(Document.CHUNK_SIZE):  # async read chunk
					await out_file.write(content)  # async write chunk

		return await cls.create(
			original_name=original_filename,
			name=new_filename,
			path=new_path
		)

	class PydanticMeta:
		computed = (
			'public_path',
		)
		exclude = (
			'bug_documents',
			'project_documents',
			'category',
			'path',
			'name'
		)
from tortoise import Tortoise
from tortoise.contrib.pydantic.creator import pydantic_queryset_creator, pydantic_model_creator

import api_v1.projects
from api_v1.projects.models import *

Tortoise.init_models([
	"api_v1.projects.models",
], "models")

User_Pydantic = pydantic_model_creator(
	cls = User,
	exclude = (
		'password',
		'bugs',
		'comments',
		'projects',
		'threadreplys',
		'user_allocated_bugs',
	),
	include = ('id', 'username', ),
	computed = ('is_authenticated', )
)
UserListing_Pydantic = pydantic_model_creator(
	cls = User,
	include = (
		'id',
		'username',
	)
)
Bug_Pydantic = pydantic_model_creator(
	cls = Bug,
	exclude = (
		'owner.password',
		'owner.bugs',
		'owner.comments',
		'owner.is_authenticated',
		'owner.threadreplys',
		'owner.user_allocated_bugs',
		'project',
	),
)
Project_Pydantic = pydantic_model_creator(
	cls = Project,
	exclude = (
		'author.password',
		'author.bugs',
		'author.comments',
		'author.projects',
		'author.threadreplys',
		'author.threads',
		'author.is_authenticated',
		'author.user_allocated_bugs',

		'bugs.owner.password',
		'bugs.owner.comments',
		'bugs.owner.bugs',
		'bugs.owner.projects',
		'bugs.owner.threadreplys',
		'bugs.owner.threads',
		'bugs.owner.user_allocated_bugs',

		'bugs.comments',
		'bugs.project',
		'bugs.threads',
		'bugs.threadreplys',

		'comments.project',
		'comments.bug',
		'comments.author.password',
		'comments.author.comments',
		'comments.author.bugs',
		'comments.author.projects',
		'comments.author.threadreplys',
		'comments.author.threads',
		'comments.author.user_allocated_bugs',
		
		'client.projects',

		'threadreplys',

		'threads.project',
		'threads.threadreplys',
		'threads.author.password',
		'threads.author.bugs',
		'threads.author.comments',
		'threads.author.projects',
		'threads.author.is_authenticated',
		'threads.author.threadreplys',
		'threads.author.threads',
		'threads.author.user_allocated_bugs',

		'badges.bug_badges',
		'badges.project_badges',
		'bugs.badges.bug_badges',
		'bugs.badges.project_badges'
	),
	allow_cycles=True
)
ProjectListing_Pydantic = pydantic_model_creator(
	cls = Project,
	exclude = (
		'author.password',
		'author.bugs',
		'author.comments',
		'author.projects',
		'author.is_authenticated',
		'author.threadreplys',
		'author.threads',
		'author.user_allocated_bugs',

		'bugs',
		'comments',
		'threadreplys',
		
		'client.projects',

		'threads.project',
		'threads.threadreplys',
		'threads.author.password',
		'threads.author.bugs',
		'threads.author.comments',
		'threads.author.projects',
		'threads.author.is_authenticated',
		'threads.author.threadreplys',
		'threads.author.threads',
		'threads.author.user_allocated_bugs',

		'badges.bug_badges',
		'badges.project_badges',
		'bugs.badges.bug_badges',
		'bugs.badges.project_badges'
	),
	computed = (
		'bug_count',
		'comment_count'
	),
	allow_cycles=True
)
Organisation_Pydantic = pydantic_model_creator(
	cls = Organisation,
	exclude = ("projects", )
)
ObjectHistory_Pydantic = pydantic_model_creator(
	cls = ObjectHistory,
	exclude=(
		'attribute_type',
		'attribute_prior_state',
		'attribute_new_state',
		'attribute_name',
		'date_updated',
		'id',
	),
	computed=(
		'object_comment',
	)
)
CommentListing_Pydantic = pydantic_model_creator(
	cls = Comment,
	exclude = (
		'bug',
		'project',
		'author.bugs',
		'author.password',
		'author.projects',
		'author.threads', 
		'author.threadreplys',
		'author.comments',
		'author.user_allocated_bugs',
	),
	allow_cycles=True
)
ThreadListing_Pydantic = pydantic_model_creator(
	cls = Thread,
	exclude = (
		'bug',
		'project',
		'author.bugs',
		'author.password',
		'author.projects',
		'author.threads', 
		'author.threadreplys',
		'author.comments',
		'author.user_allocated_bugs',
	),
	allow_cycles=True
)
ThreadReplyListing_Pydantic = pydantic_model_creator(
	cls = ThreadReply,
	exclude = (
		'thread',
		'bug',
		'project',
		'author.bugs',
		'author.password',
		'author.projects',
		'author.threads', 
		'author.threadreplys',
		'author.comments',
		'author.user_allocated_bugs',
	),
	allow_cycles=True
)
Badge_Pydantic = pydantic_model_creator(
	cls = Badge,
	exclude=(
		'bug_badges',
		'project_badges'
	)
)
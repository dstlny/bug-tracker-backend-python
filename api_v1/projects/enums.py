from enum import Enum

class StatusEnum(str, Enum):

	OPEN: str = "Open"
	CLOSED: str = "Closed"

class PriorityEnum(str, Enum):
	
	HIGH: str = "High"
	MEDIUM: str = "Medium"
	LOW: str = "Low"


class ColorEnum(str, Enum):
	
	RED: str = "red"
	PINK: str = "pink"
	PURPLE: str = "purple"
	BLUE: str = "blue"
	LIGHT_BLUE: str = "light-blue"
	CYAN: str = "cyan"
	TEAL: str = "teal"
	GREEN: str = "green"
	LIGHT_GREEN: str = "light-green"
	LIME: str = "lime"
	YELLOW: str = "yellow"
	AMBER: str = "amber"
	ORANGE: str = "orange"
	DEEP_ORANGE: str = "deep-orange"
	BROWN: str = "brown"
	GREY: str = "grey"
	BLUE_GREY: str = "blue-grey"

class ObjectEnum(str, Enum):

	PROJECT: str = 'Project'
	BUG: str = 'Bug'


class DocumentCategoryEnum(str, Enum):

	PROJECT: str = 'Project'
	BUG: str = 'Bug'
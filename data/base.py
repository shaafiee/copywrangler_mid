from pydantic import BaseModel


class ModuleRegister(BaseModel):
	session: str
	handshake: str
	name: str | None = None
	description: str | None = None
	permissions: str | None = None
	access: str | None = None
	email: str | None = None
	key: str | None = None


class PullScope(BaseModel):
	session: str
	pages: int | None = 0
	collections: int | None = 0
	scope: str | None = None


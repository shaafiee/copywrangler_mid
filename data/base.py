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
	assets: int | None = 0
	scope: str | None = None

class PullTransScope(BaseModel):
	session: str
	resource: int | None = 0
	resourceType: int | None = 1
	scope: str | None = None

class UpdateTrans(BaseModel):
	session: str
	resource: int
	resourceType: int | None = 1
	trKey: str
	trValue: str
	lang: str

class UploadSheet(BaseModel):
	session: str
	url: str

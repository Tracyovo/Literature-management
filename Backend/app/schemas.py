from pydantic import BaseModel, Field
from typing import Optional


class CategoryBase(BaseModel):
    name: str = Field(..., max_length=100)


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str = Field(..., max_length=100)


class CategoryOut(CategoryBase):
    id: int

    class Config:
        from_attributes = True


class LiteratureBase(BaseModel):
    title: str = Field(..., max_length=255)
    authors: Optional[str] = Field(default=None, max_length=255)
    year: Optional[int] = Field(default=None, ge=1800, le=2100)
    journal: Optional[str] = Field(default=None, max_length=255)
    abstract: Optional[str] = None
    category_id: Optional[int] = None


class LiteratureCreate(LiteratureBase):
    pass


class LiteratureCreateWithUpload(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    authors: Optional[str] = Field(default=None, max_length=255)
    year: Optional[int] = Field(default=None, ge=1800, le=2100)
    journal: Optional[str] = Field(default=None, max_length=255)
    abstract: Optional[str] = None
    category_id: Optional[int] = None


class LiteratureUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    authors: Optional[str] = Field(default=None, max_length=255)
    year: Optional[int] = Field(default=None, ge=1800, le=2100)
    journal: Optional[str] = Field(default=None, max_length=255)
    abstract: Optional[str] = None
    category_id: Optional[int] = None


class LiteratureOut(LiteratureBase):
    id: int
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    content_text: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class StorageRootUpdate(BaseModel):
    storage_root: str


class AgentSuggestRequest(BaseModel):
    literature_id: Optional[int] = None
    text: Optional[str] = None
    filename: Optional[str] = None


class AgentSuggestResponse(BaseModel):
    title: Optional[str] = None
    authors: Optional[str] = None
    year: Optional[int] = None
    category_suggest: Optional[str] = None


class AgentStatusResponse(BaseModel):
    available: bool
    mode: str

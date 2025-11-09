from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum as PyEnum

class AttrCategory(PyEnum):
    entity = "entity"
    component = "component"
    rule = "rule"
    measure = "measure"
    other = "other"

class ConvertPhysReq(BaseModel):
    namespace: str = Field(default="default")
    entity: str
    physical_names: List[str]

class ConvertLogiReq(BaseModel):
    namespace: str = Field(default="default")
    entity: str
    logical_names: List[str]

class AttributeIn(BaseModel):
    namespace: str = "default"
    entity: str
    category: AttrCategory = AttrCategory.entity
    logical_name: str
    physical_name: str
    data_type: str
    description: Optional[str] = None
    source_system: Optional[str] = None
    owner: Optional[str] = None
    synonyms: List[str] = []
    tags: List[str] = []
    is_active: bool = True
    metadata: dict = {}

class AttributeOut(AttributeIn):
    id: int
    version: int

class SearchResp(BaseModel):
    items: List[AttributeOut]
    total: int | None = None

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, or_, tuple_
import sqlalchemy
from api.app.repo.db import Attribute
from typing import Sequence

class DuplicateError(Exception):
    """Raised when one or more rows would violate unique constraints."""
    def __init__(self, duplicates: list[tuple]):
        self.duplicates = duplicates
        super().__init__(f"Duplicate rows found: {duplicates}")

class MigrationError(Exception):
    """Raised when the required DB schema/table is missing (migrations not applied)."""
    pass

# Helper to normalize a single input row so DB driver receives plain Python types
def _normalize_row(r: dict) -> dict:
    r2 = dict(r)
    if "category" in r2 and r2["category"] is not None:
        cat = r2["category"]
        # If it's a Python Enum, extract its value; otherwise leave as-is
        if hasattr(cat, "value"):
            cat = cat.value
        r2["category"] = str(cat).strip()
    return r2

class AttributeRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_physical(self, ns: str, entity: str, physical: str) -> Attribute | None:
        q = select(Attribute).where(
            Attribute.namespace == ns,
            Attribute.entity == entity,
            Attribute.physical_name == physical,
            Attribute.is_active == True
        ).limit(1)
        return (await self.session.execute(q)).scalars().first()

    async def get_by_logical(self, ns: str, entity: str, logical: str) -> Attribute | None:
        q = select(Attribute).where(
            Attribute.namespace == ns,
            Attribute.entity == entity,
            Attribute.logical_name == logical,
            Attribute.is_active == True
        ).limit(1)
        return (await self.session.execute(q)).scalars().first()

    async def bulk_insert(self, rows: list[dict]) -> Sequence[Attribute]:
        # Normalize rows so category is a plain string (DB enum expects that form)
        normalized = [_normalize_row(r) for r in rows]

        # Pre-check for duplicates in DB to give a friendly error instead of a 500
        keys = [(r.get('namespace','default'), r.get('entity'), r.get('physical_name')) for r in normalized]
        # Remove None keys and duplicates in input
        keys = [k for k in keys if k[1] is not None and k[2] is not None]
        keys_set = list(dict.fromkeys(keys))

        if keys_set:
            stmt = select(Attribute.namespace, Attribute.entity, Attribute.physical_name).where(
                tuple_(Attribute.namespace, Attribute.entity, Attribute.physical_name).in_(keys_set)
            )
            try:
                res = await self.session.execute(stmt)
            except sqlalchemy.exc.ProgrammingError as e:
                # Likely the meta.attribute table or enum doesn't exist (migrations not applied)
                raise MigrationError(str(e))

            existing = set(res.all())
            if existing:
                # Convert rows to list of tuples for the exception
                dup_list = [tuple(x) for x in existing]
                raise DuplicateError(dup_list)

        objs = [Attribute(**r) for r in normalized]
        self.session.add_all(objs)
        await self.session.flush()
        return objs

    async def update(self, id_: int, payload: dict) -> int:
        res = await self.session.execute(update(Attribute).where(Attribute.id == id_).values(**payload))
        return res.rowcount or 0

    async def delete(self, id_: int) -> int:
        res = await self.session.execute(delete(Attribute).where(Attribute.id == id_))
        return res.rowcount or 0

    async def search(self, ns: str | None, entity: str | None, q: str | None, by: str, limit: int, offset: int):
        stmt = select(Attribute).where(Attribute.is_active == True)
        if ns: stmt = stmt.where(Attribute.namespace == ns)
        if entity: stmt = stmt.where(Attribute.entity == entity)
        if q:
            if by == "logical":
                stmt = stmt.where(Attribute.logical_name.ilike(f"%{q}%"))
            elif by == "physical":
                stmt = stmt.where(Attribute.physical_name.ilike(f"%{q}%"))
            else:
                stmt = stmt.where(or_(Attribute.logical_name.ilike(f"%{q}%"),
                                      Attribute.physical_name.ilike(f"%{q}%")))
        stmt = stmt.limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return res.scalars().all()

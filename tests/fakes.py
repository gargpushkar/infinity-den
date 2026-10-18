"""A tiny in-memory stand-in for the Motor collections the services use.

Supports only what the tests need: equality, $or, $lte, $ne, $in, $nin, $set, a counting
aggregate, sort,
limit, and optional unique keys. Not a MongoDB emulator.
"""

from typing import Any

from bson import ObjectId
from pymongo.errors import DuplicateKeyError


def _matches(document: dict[str, Any], query: dict[str, Any]) -> bool:
    for key, condition in query.items():
        if key == "$or":
            if not any(_matches(document, option) for option in condition):
                return False
            continue
        value = document.get(key)
        if isinstance(condition, dict):
            for operator, operand in condition.items():
                if operator == "$lte" and not (value is not None and value <= operand):
                    return False
                if operator == "$ne" and value == operand:
                    return False
                if operator == "$in" and value not in operand:
                    return False
                if operator == "$nin" and value in operand:
                    return False
        elif value != condition:
            return False
    return True


def _sorted(documents: list[dict], sort: list[tuple[str, int]] | None) -> list[dict]:
    for field, direction in reversed(sort or []):
        documents = sorted(documents, key=lambda d: d.get(field), reverse=direction < 0)
    return documents


class FakeCursor:
    def __init__(self, documents: list[dict]) -> None:
        self.documents = documents
        self._sort: list[tuple[str, int]] | None = None
        self._limit: int | None = None

    def sort(self, sort, direction=1):
        # Motor accepts both sort("field", 1) and sort([("field", 1), ...]).
        self._sort = [(sort, direction)] if isinstance(sort, str) else sort
        return self

    def limit(self, count):
        self._limit = count
        return self

    def __aiter__(self):
        documents = _sorted(self.documents, self._sort)[: self._limit]

        async def iterate():
            for document in documents:
                yield dict(document)
        return iterate()


class FakeCollection:
    def __init__(self, documents=None, *, unique: tuple[str, ...] = ()) -> None:
        # Like MongoDB, every stored document has an _id.
        self.documents = [{"_id": ObjectId(), **d} for d in documents or []]
        self.unique = unique

    async def count_documents(self, query, **_kwargs):
        return sum(_matches(d, query) for d in self.documents)

    async def find_one(self, query, *_args, sort=None, **_kwargs):
        found = _sorted([d for d in self.documents if _matches(d, query)], sort)
        return dict(found[0]) if found else None

    def find(self, query, *_args, **_kwargs):
        return FakeCursor([d for d in self.documents if _matches(d, query)])

    def aggregate(self, pipeline):
        """Only $match, $unwind, and a $group that counts ({"$sum": 1})."""
        rows = [dict(d) for d in self.documents]
        for stage in pipeline:
            (operator, spec), = stage.items()
            if operator == "$match":
                rows = [d for d in rows if _matches(d, spec)]
            elif operator == "$unwind":
                field = spec.lstrip("$")
                rows = [{**d, field: value} for d in rows for value in d.get(field) or []]
            elif operator == "$group":
                key = spec["_id"].lstrip("$")
                name = next(k for k in spec if k != "_id")
                counts: dict = {}
                for d in rows:
                    counts[d.get(key)] = counts.get(d.get(key), 0) + 1
                rows = [{"_id": k, name: v} for k, v in counts.items()]
        return FakeCursor(rows)

    async def insert_one(self, document):
        if self.unique and any(all(d.get(k) == document.get(k) for k in self.unique) for d in self.documents):
            raise DuplicateKeyError("duplicate key")
        document = {**document, "_id": document.get("_id", ObjectId())}
        self.documents.append(document)
        return type("InsertResult", (), {"inserted_id": document["_id"]})()

    async def find_one_and_update(self, query, update, **_kwargs):
        for document in self.documents:
            if _matches(document, query):
                document.update(update["$set"])
                return dict(document)
        return None

    async def update_one(self, query, update, **_kwargs):
        return await self.update_many(query, update, limit=1)

    async def update_many(self, query, update, *, limit=None, **_kwargs):
        changed = 0
        for document in self.documents:
            if _matches(document, query) and (limit is None or changed < limit):
                document.update(update["$set"])
                changed += 1
        return type("UpdateResult", (), {"modified_count": changed, "matched_count": changed})()

    async def find_one_and_delete(self, query, *_args, **_kwargs):
        for index, document in enumerate(self.documents):
            if _matches(document, query):
                return dict(self.documents.pop(index))
        return None

    async def delete_one(self, query):
        for index, document in enumerate(self.documents):
            if _matches(document, query):
                del self.documents[index]
                return type("DeleteResult", (), {"deleted_count": 1})()
        return type("DeleteResult", (), {"deleted_count": 0})()

    async def delete_many(self, query):
        before = len(self.documents)
        self.documents = [d for d in self.documents if not _matches(d, query)]
        return type("DeleteResult", (), {"deleted_count": before - len(self.documents)})()

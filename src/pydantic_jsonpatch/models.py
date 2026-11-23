from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator
from pydantic_jsonpointer import JsonPointer


class Operation(str, Enum):
    ADD = "add"
    REMOVE = "remove"
    REPLACE = "replace"
    MOVE = "move"
    COPY = "copy"
    TEST = "test"


class JsonPatchAdd(BaseModel):
    op: Literal[Operation.ADD] = Operation.ADD
    path: JsonPointer
    value: Any


class JsonPatchRemove(BaseModel):
    op: Literal[Operation.REMOVE] = Operation.REMOVE
    path: JsonPointer


class JsonPatchReplace(BaseModel):
    op: Literal[Operation.REPLACE] = Operation.REPLACE
    path: JsonPointer
    value: Any


class JsonPatchMove(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    op: Literal[Operation.MOVE] = Operation.MOVE
    path: JsonPointer
    from_: JsonPointer = Field(alias="from")

    @model_validator(mode="after")
    def _check_from_not_prefix_of_path(self) -> JsonPatchMove:
        from_tokens = self.from_.tokens
        path_tokens = self.path.tokens
        if (
            len(from_tokens) < len(path_tokens)
            and path_tokens[: len(from_tokens)] == from_tokens
        ):
            msg = f"'from' ({self.from_}) must not be a proper prefix of 'path' ({self.path})"
            raise ValueError(msg)
        return self


class JsonPatchCopy(BaseModel):
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)
    op: Literal[Operation.COPY] = Operation.COPY
    path: JsonPointer
    from_: JsonPointer = Field(alias="from")


class JsonPatchTest(BaseModel):
    op: Literal[Operation.TEST] = Operation.TEST
    path: JsonPointer
    value: Any


JsonPatchItem = Annotated[
    Union[
        JsonPatchAdd,
        JsonPatchRemove,
        JsonPatchReplace,
        JsonPatchMove,
        JsonPatchCopy,
        JsonPatchTest,
    ],
    Field(discriminator="op"),
]


class JsonPatch(RootModel[list[JsonPatchItem]]):
    """RFC 6902 JSON Patch document.

    Can be constructed directly or built incrementally via chaining::

        patch = JsonPatch().add("/a", 1).remove("/b").replace("/c", "new")
    """

    root: list[JsonPatchItem] = []

    def add(self, path: str, value: Any) -> JsonPatch:
        self.root.append(JsonPatchAdd(path=path, value=value))
        return self

    def remove(self, path: str) -> JsonPatch:
        self.root.append(JsonPatchRemove(path=path))
        return self

    def replace(self, path: str, value: Any) -> JsonPatch:
        self.root.append(JsonPatchReplace(path=path, value=value))

        return self

    def move(self, path: str, *, from_: str) -> JsonPatch:
        self.root.append(
            JsonPatchMove(path=path, from_=from_)  # ty: ignore[missing-argument, unknown-argument]
        )
        return self

    def copy(  # type: ignore[override]  # ty: ignore[invalid-method-override]
        self, path: str, *, from_: str
    ) -> JsonPatch:
        self.root.append(
            JsonPatchCopy(path=path, from_=from_)  # ty: ignore[missing-argument, unknown-argument]
        )
        return self

    def test(self, path: str, value: Any) -> JsonPatch:
        self.root.append(JsonPatchTest(path=path, value=value))
        return self

    def serialize(self) -> str:
        return self.model_dump_json(by_alias=True)

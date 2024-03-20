from typing import Type, TypeVar, Optional, Callable, Sequence, Union
from enum import Enum
import forge

from fastapi import Depends, Body, Query, APIRouter, params
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from pydantic import BaseModel, ValidationError

from ..exceptions.http_exceptions import NotFoundException
from ..crud.fast_crud import FastCRUD
from ..exceptions.http_exceptions import DuplicateValueException
from .helper import CRUDMethods, _get_primary_keys, _extract_unique_columns
from ..paginated.response import paginated_response
from ..paginated.helper import compute_offset

CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
UpdateSchemaInternalType = TypeVar("UpdateSchemaInternalType", bound=BaseModel)
DeleteSchemaType = TypeVar("DeleteSchemaType", bound=BaseModel)


class EndpointCreator:
    """
    A class to create and register CRUD endpoints for a FastAPI application.

    This class simplifies the process of adding create, read, update, and delete (CRUD) endpoints
    to a FastAPI router. It is initialized with a SQLAlchemy session, model, CRUD operations,
    and Pydantic schemas, and allows for custom dependency injection for each endpoint.
    The method assumes 'id' is the primary key for path parameters.

    Attributes:
        session: The SQLAlchemy async session.
        model: The SQLAlchemy model.
        crud: An optional FastCRUD instance. If not provided, uses FastCRUD(model).
        create_schema: Pydantic schema for creating an item.
        update_schema: Pydantic schema for updating an item.
        delete_schema: Optional Pydantic schema for deleting an item.
        include_in_schema: Whether to include the created endpoints in the OpenAPI schema.
        path: Base path for the CRUD endpoints.
        tags: List of tags for grouping endpoints in the documentation.
        is_deleted_column: Optional column name to use for indicating a soft delete. Defaults to "is_deleted".
        deleted_at_column: Optional column name to use for storing the timestamp of a soft delete. Defaults to "deleted_at".
        updated_at_column: Optional column name to use for storing the timestamp of an update. Defaults to "updated_at".
        endpoint_names: Optional dictionary to customize endpoint names for CRUD operations. Keys are operation types
                        ("create", "read", "update", "delete", "db_delete", "read_multi", "read_paginated"), and
                        values are the custom names to use. Unspecified operations will use default names.

    Raises:
        ValueError: If both `included_methods` and `deleted_methods` are provided.

    Examples:
        Basic Setup:
        ```python
        from fastapi import FastAPI
        from fastcrud import EndpointCreator

        from myapp.models import MyModel
        from myapp.schemas import CreateMyModel, UpdateMyModel
        from myapp.database import async_session

        app = FastAPI()
        endpoint_creator = EndpointCreator(
            session=async_session,
            model=MyModel,
            create_schema=CreateMyModel,
            update_schema=UpdateMyModel
        )
        endpoint_creator.add_routes_to_router()
        app.include_router(endpoint_creator.router, prefix="/mymodel")
        ```

        With Custom Dependencies:
        ```python
        from fastapi.security import OAuth2PasswordBearer

        oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

        def get_current_user(token: str = Depends(oauth2_scheme)):
            return ...

        endpoint_creator.add_routes_to_router(
            read_deps=[get_current_user],
            update_deps=[get_current_user]
        )
        ```

        Selective Endpoint Creation (inclusion):
        ```python
        # Only create 'create' and 'read' endpoints
        endpoint_creator.add_routes_to_router(
            included_methods=["create", "read"]
        )
        ```

        Selective Endpoint Creation (deletion):
        ```python
        # Create all but 'update' and 'delete' endpoints
        endpoint_creator.add_routes_to_router(
            deleted_methods=["update", "delete"]
        )
        ```

        Integrating with Multiple Models:
        ```python
        # Assuming definitions for OtherModel, CRUDOtherModel, etc.

        other_model_crud = CRUDOtherModel(OtherModel)
        other_endpoint_creator = EndpointCreator(
            session=async_session,
            model=OtherModel,
            crud=other_model_crud,
            create_schema=CreateOtherModel,
            update_schema=UpdateOtherModel
        )
        other_endpoint_creator.add_routes_to_router()
        app.include_router(other_endpoint_creator.router, prefix="/othermodel")
        ```

        Customizing Endpoint Names:
        ```python
        endpoint_creator = EndpointCreator(
            session=async_session,
            model=MyModel,
            create_schema=CreateMyModel,
            update_schema=UpdateMyModel,
            path="/mymodel",
            tags=["MyModel"],
            endpoint_names={
                "create": "add",  # Custom endpoint name for creating items
                "read": "fetch",  # Custom endpoint name for reading a single item
                "update": "change",  # Custom endpoint name for updating items
                # The delete operation will use the default name "delete"
            }
        )
        endpoint_creator.add_routes_to_router()
        ```
    """

    def __init__(
        self,
        session: Callable,
        model: type[DeclarativeBase],
        create_schema: Type[CreateSchemaType],
        update_schema: Type[UpdateSchemaType],
        crud: Optional[FastCRUD] = None,
        include_in_schema: bool = True,
        delete_schema: Optional[Type[DeleteSchemaType]] = None,
        path: str = "",
        tags: Optional[list[Union[str, Enum]]] = None,
        is_deleted_column: str = "is_deleted",
        deleted_at_column: str = "deleted_at",
        updated_at_column: str = "updated_at",
        endpoint_names: Optional[dict[str, str]] = None,
    ) -> None:
        self._primary_keys = _get_primary_keys(model)
        self._primary_keys_types = {
            pk.name: pk.type.python_type for pk in self._primary_keys
        }
        self.primary_key_names = [pk.name for pk in self._primary_keys]
        self.session = session
        self.crud = crud or FastCRUD(
            model=model,
            is_deleted_column=is_deleted_column,
            deleted_at_column=deleted_at_column,
            updated_at_column=updated_at_column,
        )
        self.model = model
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.delete_schema = delete_schema
        self.include_in_schema = include_in_schema
        self.path = path
        self.tags = tags or []
        self.router = APIRouter()
        self.is_deleted_column = is_deleted_column
        self.deleted_at_column = deleted_at_column
        self.updated_at_column = updated_at_column
        self.default_endpoint_names = {
            "create": "create",
            "read": "get",
            "update": "update",
            "delete": "delete",
            "db_delete": "db_delete",
            "read_multi": "get_multi",
            "read_paginated": "get_paginated",
        }
        self.endpoint_names = {**self.default_endpoint_names, **(endpoint_names or {})}

    def _create_item(self):
        """Creates an endpoint for creating items in the database."""

        async def endpoint(
            db: AsyncSession = Depends(self.session),
            item: self.create_schema = Body(...),  # type: ignore
        ):
            unique_columns = _extract_unique_columns(self.model)

            for column in unique_columns:
                col_name = column.name
                if hasattr(item, col_name):
                    value = getattr(item, col_name)
                    exists = await self.crud.exists(db, **{col_name: value})
                    if exists:
                        raise DuplicateValueException(
                            f"Value {value} is already registered"
                        )

            return await self.crud.create(db, item)

        return endpoint

    def _read_item(self):
        """Creates an endpoint for reading a single item from the database."""

        @forge.sign(
            *[forge.arg(k, type=v) for k, v in self._primary_keys_types.items()],
            forge.arg("db", type=AsyncSession, default=Depends(self.session)),
        )
        async def endpoint(db: AsyncSession = Depends(self.session), **pkeys):
            item = await self.crud.get(db, **pkeys)
            if not item:
                raise NotFoundException(detail="Item not found")
            return item

        return endpoint

    def _read_items(self):
        """Creates an endpoint for reading multiple items from the database."""

        async def endpoint(
            db: AsyncSession = Depends(self.session),
            offset: int = Query(0),
            limit: int = Query(100),
        ):
            return await self.crud.get_multi(db, offset=offset, limit=limit)

        return endpoint

    def _read_paginated(self):
        """Creates an endpoint for reading multiple items from the database with pagination."""

        async def endpoint(
            db: AsyncSession = Depends(self.session),
            page: int = Query(
                1, alias="page", description="Page number, starting from 1"
            ),
            items_per_page: int = Query(
                10, alias="itemsPerPage", description="Number of items per page"
            ),
        ):
            offset = compute_offset(page=page, items_per_page=items_per_page)
            crud_data = await self.crud.get_multi(
                db, offset=offset, limit=items_per_page
            )

            return paginated_response(
                crud_data=crud_data, page=page, items_per_page=items_per_page
            )

        return endpoint

    def _update_item(self):
        """Creates an endpoint for updating an existing item in the database."""

        @forge.sign(
            *[forge.arg(k, type=v) for k, v in self._primary_keys_types.items()],
            forge.arg("item", type=self.update_schema, default=Body(...)),
            forge.arg("db", type=AsyncSession, default=Depends(self.session)),
        )
        async def endpoint(
            item: self.update_schema = Body(...),  # type: ignore
            db: AsyncSession = Depends(self.session),
            **pkeys,
        ):
            return await self.crud.update(db, item, **pkeys)

        return endpoint

    def _delete_item(self):
        """Creates an endpoint for deleting an item from the database."""

        @forge.sign(
            *[forge.arg(k, type=v) for k, v in self._primary_keys_types.items()],
            forge.arg("db", type=AsyncSession, default=Depends(self.session)),
        )
        async def endpoint(db: AsyncSession = Depends(self.session), **pkeys):
            await self.crud.delete(db, **pkeys)
            return {"message": "Item deleted successfully"}

        return endpoint

    def _db_delete(self):
        """
        Creates an endpoint for hard deleting an item from the database.

        This endpoint is only added if the delete_schema is provided during initialization.
        The endpoint expects an item ID as a path parameter and uses the provided SQLAlchemy
        async session to permanently delete the item from the database.
        """

        @forge.sign(
            *[forge.arg(k, type=v) for k, v in self._primary_keys_types.items()],
            forge.arg("db", type=AsyncSession, default=Depends(self.session)),
        )
        async def endpoint(db: AsyncSession = Depends(self.session), **pkeys):
            await self.crud.db_delete(db, **pkeys)
            return {"message": "Item permanently deleted from the database"}

        return endpoint

    def _get_endpoint_name(self, operation: str) -> str:
        """Get the endpoint name for a given CRUD operation, using defaults if not overridden by the user."""
        return self.endpoint_names.get(
            operation, self.default_endpoint_names.get(operation, operation)
        )

    def add_routes_to_router(
        self,
        create_deps: Sequence[params.Depends] = [],
        read_deps: Sequence[params.Depends] = [],
        read_multi_deps: Sequence[params.Depends] = [],
        read_paginated_deps: Sequence[params.Depends] = [],
        update_deps: Sequence[params.Depends] = [],
        delete_deps: Sequence[params.Depends] = [],
        db_delete_deps: Sequence[params.Depends] = [],
        included_methods: Optional[Sequence[str]] = None,
        deleted_methods: Optional[Sequence[str]] = None,
    ):
        """
        Adds CRUD operation routes to the FastAPI router with specified dependencies for each type of operation.

        This method registers routes for create, read, update, and delete operations with the FastAPI router,
        allowing for custom dependency injection for each type of operation.

        Args:
            create_deps: List of dependency injection functions for the create endpoint.
            read_deps: List of dependency injection functions for the read endpoint.
            read_multi_deps: List of dependency injection functions for the read multiple items endpoint.
            update_deps: List of dependency injection functions for the update endpoint.
            delete_deps: List of dependency injection functions for the delete endpoint.
            db_delete_deps: List of dependency injection functions for the hard delete endpoint.
            included_methods: Optional list of methods to include. Defaults to all CRUD methods.
            deleted_methods: Optional list of methods to exclude. Defaults to None.

        Raises:
            ValueError: If both `included_methods` and `deleted_methods` are provided.

        Examples:
            Selective Endpoint Creation:
            ```python
            # Only create 'create' and 'read' endpoints
            endpoint_creator.add_routes_to_router(
                included_methods=["create", "read"]
            )
            ```

            Excluding Specific Endpoints:
            ```python
            # Create all endpoints except 'delete' and 'db_delete'
            endpoint_creator.add_routes_to_router(
                deleted_methods=["delete", "db_delete"]
            )
            ```

            With Custom Dependencies and Selective Endpoints:
            ```python
            def get_current_user(...):
                ...

            # Create only 'read' and 'update' endpoints with custom dependencies
            endpoint_creator.add_routes_to_router(
                read_deps=[get_current_user],
                update_deps=[get_current_user],
                included_methods=["read", "update"]
            )
            ```

        Note:
            This method should be called to register the endpoints with the FastAPI application.
            If 'delete_schema' is provided, a hard delete endpoint is also registered.
            This method assumes 'id' is the primary key for path parameters.
        """
        if (included_methods is not None) and (deleted_methods is not None):
            raise ValueError(
                "Cannot use both 'included_methods' and 'deleted_methods' simultaneously."
            )

        if included_methods is None:
            included_methods = [
                "create",
                "read",
                "read_multi",
                "read_paginated",
                "update",
                "delete",
                "db_delete",
            ]
        else:
            try:
                included_methods = CRUDMethods(
                    valid_methods=included_methods
                ).valid_methods
            except ValidationError as e:
                raise ValueError(f"Invalid CRUD methods in included_methods: {e}")

        if deleted_methods is None:
            deleted_methods = []
        else:
            try:
                deleted_methods = CRUDMethods(
                    valid_methods=deleted_methods
                ).valid_methods
            except ValidationError as e:
                raise ValueError(f"Invalid CRUD methods in deleted_methods: {e}")

        delete_description = "Delete a"
        if self.delete_schema:
            delete_description = "Soft delete a"

        if ("create" in included_methods) and ("create" not in deleted_methods):
            endpoint_name = self._get_endpoint_name("create")
            self.router.add_api_route(
                f"{self.path}/{endpoint_name}",
                self._create_item(),
                methods=["POST"],
                include_in_schema=self.include_in_schema,
                tags=self.tags,
                dependencies=create_deps,
                description=f"Create a new {self.model.__name__} row in the database.",
            )

        if ("read" in included_methods) and ("read" not in deleted_methods):
            endpoint_name = self._get_endpoint_name("read")

            self.router.add_api_route(
                f"{self.path}/{endpoint_name}/{'/'.join(f'{{{n}}}' for n in self.primary_key_names)}",
                self._read_item(),
                methods=["GET"],
                include_in_schema=self.include_in_schema,
                tags=self.tags,
                dependencies=read_deps,
                description=f"Read a single {self.model.__name__} row from the database by its primary keys: {self.primary_key_names}.",
            )

        if ("read_multi" in included_methods) and ("read_multi" not in deleted_methods):
            endpoint_name = self._get_endpoint_name("read_multi")
            self.router.add_api_route(
                f"{self.path}/{endpoint_name}",
                self._read_items(),
                methods=["GET"],
                include_in_schema=self.include_in_schema,
                tags=self.tags,
                dependencies=read_multi_deps,
                description=f"Read multiple {self.model.__name__} rows from the database with a limit and an offset.",
            )

        if ("read_paginated" in included_methods) and (
            "read_paginated" not in deleted_methods
        ):
            endpoint_name = self._get_endpoint_name("read_paginated")
            self.router.add_api_route(
                f"{self.path}/{endpoint_name}",
                self._read_paginated(),
                methods=["GET"],
                include_in_schema=self.include_in_schema,
                tags=self.tags,
                dependencies=read_paginated_deps,
                description=f"Read multiple {self.model.__name__} rows from the database with pagination.",
            )

        if ("update" in included_methods) and ("update" not in deleted_methods):
            endpoint_name = self._get_endpoint_name("update")
            self.router.add_api_route(
                f"{self.path}/{endpoint_name}/{'/'.join(f'{{{n}}}' for n in self.primary_key_names)}",
                self._update_item(),
                methods=["PATCH"],
                include_in_schema=self.include_in_schema,
                tags=self.tags,
                dependencies=update_deps,
                description=f"Update an existing {self.model.__name__} row in the database by its primary keys: {self.primary_key_names}.",
            )

        if ("delete" in included_methods) and ("delete" not in deleted_methods):
            endpoint_name = self._get_endpoint_name("delete")
            self.router.add_api_route(
                f"{self.path}/{endpoint_name}/{'/'.join(f'{{{n}}}' for n in self.primary_key_names)}",
                self._delete_item(),
                methods=["DELETE"],
                include_in_schema=self.include_in_schema,
                tags=self.tags,
                dependencies=delete_deps,
                description=f"{delete_description} {self.model.__name__} row from the database by its primary keys: {self.primary_key_names}.",
            )

        if (
            ("db_delete" in included_methods)
            and ("db_delete" not in deleted_methods)
            and self.delete_schema
        ):
            endpoint_name = self._get_endpoint_name("db_delete")
            self.router.add_api_route(
                f"{self.path}/{endpoint_name}/{'/'.join(f'{{{n}}}' for n in self.primary_key_names)}",
                self._db_delete(),
                methods=["DELETE"],
                include_in_schema=self.include_in_schema,
                tags=self.tags,
                dependencies=db_delete_deps,
                description=f"Permanently delete a {self.model.__name__} row from the database by its primary keys: {self.primary_key_names}.",
            )

    def add_custom_route(
        self,
        endpoint: Callable,
        methods: Optional[Union[set[str], list[str]]],
        path: Optional[str] = None,
        dependencies: Optional[Sequence[params.Depends]] = None,
        include_in_schema: bool = True,
        tags: Optional[list[Union[str, Enum]]] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        response_description: str = "Successful Response",
    ) -> None:
        """
        Adds a custom route to the FastAPI router.

        Args:
            path: URL path for the custom route.
            endpoint: The endpoint function to execute when the route is called.
            methods: A list of HTTP methods for the route (e.g., ['GET', 'POST']).
            dependencies: A list of dependency injection functions for the route.
            include_in_schema: Whether to include this route in the OpenAPI schema.
            tags: Tags for grouping and categorizing the route in documentation.
            summary: A short summary of the route, for documentation.
            description: A detailed description of the route, for documentation.
            response_description: A description of the response, for documentation.

        Example:
            ```python
            async def custom_endpoint(foo: int, bar: str):
                # custom logic here
                return {"foo": foo, "bar": bar}

            endpoint_creator.add_custom_route(
                endpoint=custom_endpoint,
                path="/custom",
                methods=["GET"],
                tags=["custom"],
                summary="Custom Endpoint",
                description="This is a custom endpoint."
            )
            ```
        """
        path = path or self.path
        full_path = f"{self.path}{path}"
        self.router.add_api_route(
            path=full_path,
            endpoint=endpoint,
            methods=methods,
            dependencies=dependencies or [],
            include_in_schema=include_in_schema,
            tags=tags or self.tags,
            summary=summary,
            description=description,
            response_description=response_description,
        )

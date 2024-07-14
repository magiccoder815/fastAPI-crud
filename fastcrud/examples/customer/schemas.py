# --8<-- [start:imports]
from pydantic import BaseModel


# --8<-- [end:imports]
# --8<-- [start:schemas]
# --8<-- [start:createschema]
class CreateCustomerSchema(BaseModel):
    name: str | None = None


# --8<-- [end:createschema]
# --8<-- [start:readschema]
class ReadCustomerSchema(BaseModel):
    id: int
    name: str | None = None


# --8<-- [end:readschema]
# --8<-- [start:updateschema]
class UpdateCustomerSchema(BaseModel):
    name: str | None = None


# --8<-- [end:updateschema]
# --8<-- [start:deleteschema]
class DeleteCustomerSchema(BaseModel):
    pass


# --8<-- [end:deleteschema]
# --8<-- [end:schemas]

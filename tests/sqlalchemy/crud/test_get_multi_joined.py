from typing import Annotated
import pytest
from fastcrud import FastCRUD, JoinConfig, aliased
from pydantic import BaseModel, Field
from ...sqlalchemy.conftest import (
    ModelTest,
    TierModel,
    CreateSchemaTest,
    TierSchemaTest,
    ReadSchemaTest,
    CategoryModel,
    CategorySchemaTest,
    BookingModel,
    BookingSchema,
    Project,
    Participant,
    ProjectsParticipantsAssociation,
    Article,
    Card,
    ArticleSchema,
    CardSchema,
)


class JoinedTestTier(BaseModel):
    name: str
    tier_id: int
    tier_name: str


class CustomCreateSchemaTest(BaseModel):
    name: Annotated[str, Field(max_length=20)]
    tier_id: int


@pytest.mark.asyncio
async def test_get_multi_joined_basic(async_session, test_data, test_data_tier):
    for tier_item in test_data_tier:
        async_session.add(TierModel(**tier_item))
    await async_session.commit()

    for user_item in test_data:
        async_session.add(ModelTest(**user_item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)
    result = await crud.get_multi_joined(
        db=async_session,
        join_model=TierModel,
        join_prefix="tier_",
        schema_to_select=CreateSchemaTest,
        join_schema_to_select=TierSchemaTest,
        offset=0,
        limit=10,
    )

    assert len(result["data"]) == min(10, len(test_data))
    assert result["total_count"] == len(test_data)
    assert all("tier_name" in item for item in result["data"])


@pytest.mark.asyncio
async def test_get_multi_joined_unpaginated(async_session, test_data, test_data_tier):
    for tier_item in test_data_tier:
        async_session.add(TierModel(**tier_item))
    await async_session.commit()

    for user_item in test_data:
        async_session.add(ModelTest(**user_item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)
    result = await crud.get_multi_joined(
        db=async_session,
        join_model=TierModel,
        join_prefix="tier_",
        schema_to_select=CreateSchemaTest,
        join_schema_to_select=TierSchemaTest,
        offset=0,
        limit=None,
    )

    assert len(result["data"]) == len(test_data)
    assert result["total_count"] == len(test_data)
    assert all("tier_name" in item for item in result["data"])


@pytest.mark.asyncio
async def test_get_multi_joined_sorting(async_session, test_data, test_data_tier):
    for tier_item in test_data_tier:
        async_session.add(TierModel(**tier_item))
    await async_session.commit()

    for user_item in test_data:
        async_session.add(ModelTest(**user_item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)
    result = await crud.get_multi_joined(
        db=async_session,
        join_model=TierModel,
        join_prefix="tier_",
        schema_to_select=CreateSchemaTest,
        join_schema_to_select=TierSchemaTest,
        sort_columns=["name"],
        sort_orders=["asc"],
        offset=0,
        limit=10,
    )

    assert len(result["data"]) <= 10
    assert all(
        result["data"][i]["name"] <= result["data"][i + 1]["name"]
        for i in range(len(result["data"]) - 1)
    )


@pytest.mark.asyncio
async def test_get_multi_joined_filtering(async_session, test_data, test_data_tier):
    specific_user_name = "Charlie"
    for tier_item in test_data_tier:
        async_session.add(TierModel(**tier_item))
    await async_session.commit()

    for user_item in test_data:
        async_session.add(ModelTest(**user_item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)
    result = await crud.get_multi_joined(
        db=async_session,
        join_model=TierModel,
        join_prefix="tier_",
        schema_to_select=CreateSchemaTest,
        join_schema_to_select=TierSchemaTest,
        name=specific_user_name,
        offset=0,
        limit=10,
    )

    assert len(result["data"]) <= 10
    assert all(item["name"] == specific_user_name for item in result["data"])


@pytest.mark.asyncio
async def test_get_multi_joined_different_join_types(
    async_session, test_data, test_data_tier
):
    for tier_item in test_data_tier:
        async_session.add(TierModel(**tier_item))
    await async_session.commit()

    for user_item in test_data:
        async_session.add(ModelTest(**user_item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)
    for join_type in ["left", "inner"]:
        result = await crud.get_multi_joined(
            db=async_session,
            join_model=TierModel,
            join_type=join_type,
            schema_to_select=CreateSchemaTest,
            join_schema_to_select=TierSchemaTest,
            offset=0,
            limit=10,
        )

        assert len(result["data"]) <= 10


@pytest.mark.asyncio
async def test_get_multi_joined_return_model(async_session, test_data, test_data_tier):
    for tier_item in test_data_tier:
        async_session.add(TierModel(**tier_item))
    await async_session.commit()

    for user_item in test_data:
        async_session.add(ModelTest(**user_item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)
    result = await crud.get_multi_joined(
        db=async_session,
        join_model=TierModel,
        schema_to_select=JoinedTestTier,
        join_schema_to_select=TierSchemaTest,
        join_prefix="tier_",
        return_as_model=True,
        offset=0,
        limit=10,
    )

    assert all(isinstance(item, JoinedTestTier) for item in result["data"])


@pytest.mark.asyncio
async def test_get_multi_joined_no_results(async_session, test_data, test_data_tier):
    for tier_item in test_data_tier:
        async_session.add(TierModel(**tier_item))
    await async_session.commit()

    for user_item in test_data:
        async_session.add(ModelTest(**user_item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)
    result = await crud.get_multi_joined(
        db=async_session,
        join_model=TierModel,
        schema_to_select=CreateSchemaTest,
        join_schema_to_select=TierSchemaTest,
        offset=0,
        limit=10,
        name="NonExistingName",
    )

    assert len(result["data"]) == 0
    assert result["total_count"] == 0


@pytest.mark.asyncio
async def test_get_multi_joined_large_offset(async_session, test_data, test_data_tier):
    for tier_item in test_data_tier:
        async_session.add(TierModel(**tier_item))
    await async_session.commit()

    for user_item in test_data:
        async_session.add(ModelTest(**user_item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)
    result = await crud.get_multi_joined(
        db=async_session,
        join_model=TierModel,
        schema_to_select=CreateSchemaTest,
        join_schema_to_select=TierSchemaTest,
        offset=1000,
        limit=10,
    )

    assert len(result["data"]) == 0


@pytest.mark.asyncio
async def test_get_multi_joined_invalid_limit_offset(
    async_session, test_data, test_data_tier
):
    for tier_item in test_data_tier:
        async_session.add(TierModel(**tier_item))
    await async_session.commit()

    for user_item in test_data:
        async_session.add(ModelTest(**user_item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)
    with pytest.raises(ValueError):
        await crud.get_multi_joined(
            db=async_session,
            join_model=TierModel,
            schema_to_select=CreateSchemaTest,
            join_schema_to_select=TierSchemaTest,
            offset=-1,
            limit=10,
        )
    with pytest.raises(ValueError):
        await crud.get_multi_joined(
            db=async_session,
            join_model=TierModel,
            schema_to_select=CreateSchemaTest,
            join_schema_to_select=TierSchemaTest,
            offset=0,
            limit=-1,
        )


@pytest.mark.asyncio
async def test_get_multi_joined_advanced_filtering(
    async_session, test_data, test_data_tier
):
    for tier_item in test_data_tier:
        async_session.add(TierModel(**tier_item))
    await async_session.commit()

    for user_item in test_data:
        async_session.add(ModelTest(**user_item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)
    advanced_filter_result = await crud.get_multi_joined(
        db=async_session,
        join_model=TierModel,
        schema_to_select=ReadSchemaTest,
        join_schema_to_select=TierSchemaTest,
        join_prefix="tier_",
        offset=0,
        limit=10,
        id__gt=5,
    )

    assert (
        len(advanced_filter_result["data"]) > 0
    ), "Should fetch records with ID greater than 5"
    assert all(
        item["id"] > 5 for item in advanced_filter_result["data"]
    ), "All fetched records should meet the advanced filter condition"


@pytest.mark.asyncio
async def test_get_multi_joined_with_additional_join_model(
    async_session, test_data, test_data_tier, test_data_category
):
    for category_item in test_data_category:
        async_session.add(CategoryModel(**category_item))
    await async_session.commit()

    for tier_item in test_data_tier:
        async_session.add(TierModel(**tier_item))
    await async_session.commit()

    for user_item in test_data:
        async_session.add(ModelTest(**user_item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)
    result = await crud.get_multi_joined(
        db=async_session,
        joins_config=[
            JoinConfig(
                model=TierModel,
                join_prefix="tier_",
                schema_to_select=TierSchemaTest,
                join_on=ModelTest.tier_id == TierModel.id,
                join_type="left",
            ),
            JoinConfig(
                model=CategoryModel,
                join_prefix="category_",
                schema_to_select=CategorySchemaTest,
                join_on=ModelTest.category_id == CategoryModel.id,
                join_type="left",
            ),
        ],
        schema_to_select=ReadSchemaTest,
        offset=0,
        limit=10,
    )

    assert len(result["data"]) == min(10, len(test_data))
    assert result["total_count"] == len(test_data)
    assert all(
        "tier_name" in item and "category_name" in item for item in result["data"]
    )


@pytest.mark.asyncio
async def test_get_multi_joined_with_aliases(
    async_session, test_data, test_data_tier, test_data_category, test_data_booking
):
    for tier_item in test_data_tier:
        async_session.add(TierModel(**tier_item))
    for category_item in test_data_category:
        async_session.add(CategoryModel(**category_item))
    for user_item in test_data:
        async_session.add(ModelTest(**user_item))
    for booking_item in test_data_booking:
        async_session.add(BookingModel(**booking_item))
    await async_session.commit()

    crud = FastCRUD(BookingModel)

    expected_owner_name = "Charlie"
    expected_user_name = "Alice"

    owner_alias = aliased(ModelTest, name="owner")
    user_alias = aliased(ModelTest, name="user")

    result = await crud.get_multi_joined(
        db=async_session,
        schema_to_select=BookingSchema,
        joins_config=[
            JoinConfig(
                model=ModelTest,
                join_on=BookingModel.owner_id == owner_alias.id,
                join_prefix="owner_",
                alias=owner_alias,
                schema_to_select=ReadSchemaTest,
            ),
            JoinConfig(
                model=ModelTest,
                join_on=BookingModel.user_id == user_alias.id,
                join_prefix="user_",
                alias=user_alias,
                schema_to_select=ReadSchemaTest,
            ),
        ],
        offset=0,
        limit=10,
        sort_columns=["booking_date"],
        sort_orders=["asc"],
    )

    assert "data" in result and isinstance(
        result["data"], list
    ), "The result should have a 'data' key with a list of records."
    for booking in result["data"]:
        assert (
            "owner_name" in booking
        ), "Each record should include 'owner_name' from the joined owner ModelTest data."
        assert (
            "user_name" in booking
        ), "Each record should include 'user_name' from the joined user ModelTest data."
    assert result is not None
    assert result["total_count"] >= 1, "Expected at least one booking record"
    first_result = result["data"][0]
    assert (
        first_result["owner_name"] == expected_owner_name
    ), "Owner name does not match expected value"
    assert (
        first_result["user_name"] == expected_user_name
    ), "User name does not match expected value"


@pytest.mark.asyncio
async def test_get_multi_joined_with_aliases_no_schema(
    async_session, test_data, test_data_tier, test_data_category, test_data_booking
):
    for tier_item in test_data_tier:
        async_session.add(TierModel(**tier_item))
    for category_item in test_data_category:
        async_session.add(CategoryModel(**category_item))
    for user_item in test_data:
        async_session.add(ModelTest(**user_item))
    for booking_item in test_data_booking:
        async_session.add(BookingModel(**booking_item))
    await async_session.commit()

    crud = FastCRUD(BookingModel)

    expected_owner_name = "Charlie"
    expected_user_name = "Alice"

    owner_alias = aliased(ModelTest, name="owner")
    user_alias = aliased(ModelTest, name="user")

    result = await crud.get_multi_joined(
        db=async_session,
        schema_to_select=BookingSchema,
        joins_config=[
            JoinConfig(
                model=ModelTest,
                join_on=BookingModel.owner_id == owner_alias.id,
                join_prefix="owner_",
                alias=owner_alias,
            ),
            JoinConfig(
                model=ModelTest,
                join_on=BookingModel.user_id == user_alias.id,
                join_prefix="user_",
                alias=user_alias,
            ),
        ],
        offset=0,
        limit=10,
        sort_columns=["booking_date"],
        sort_orders=["asc"],
    )

    assert "data" in result and isinstance(
        result["data"], list
    ), "The result should have a 'data' key with a list of records."
    for booking in result["data"]:
        assert (
            "owner_name" in booking
        ), "Each record should include 'owner_name' from the joined owner ModelTest data."
        assert (
            "user_name" in booking
        ), "Each record should include 'user_name' from the joined user ModelTest data."
    assert result is not None
    assert result["total_count"] >= 1, "Expected at least one booking record"
    first_result = result["data"][0]
    assert (
        first_result["owner_name"] == expected_owner_name
    ), "Owner name does not match expected value"
    assert (
        first_result["user_name"] == expected_user_name
    ), "User name does not match expected value"


@pytest.mark.asyncio
async def test_many_to_many_joined(async_session):
    project1 = Project(id=1, name="Project 1", description="First Project")
    project2 = Project(id=2, name="Project 2", description="Second Project")

    participant1 = Participant(id=1, name="Participant 1", role="Developer")
    participant2 = Participant(id=2, name="Participant 2", role="Designer")

    async_session.add_all([project1, project2, participant1, participant2])
    await async_session.commit()

    projects_participants1 = ProjectsParticipantsAssociation(
        project_id=1, participant_id=1
    )
    projects_participants2 = ProjectsParticipantsAssociation(
        project_id=1, participant_id=2
    )
    projects_participants3 = ProjectsParticipantsAssociation(
        project_id=2, participant_id=1
    )

    async_session.add_all(
        [projects_participants1, projects_participants2, projects_participants3]
    )
    await async_session.commit()

    crud_project = FastCRUD(Project)

    join_condition_1 = Project.id == ProjectsParticipantsAssociation.project_id
    join_condition_2 = ProjectsParticipantsAssociation.participant_id == Participant.id

    joins_config = [
        JoinConfig(
            model=ProjectsParticipantsAssociation,
            join_on=join_condition_1,
            join_type="inner",
            join_prefix="pp_",
        ),
        JoinConfig(
            model=Participant,
            join_on=join_condition_2,
            join_type="inner",
            join_prefix="participant_",
        ),
    ]

    records = await crud_project.get_multi_joined(
        db=async_session,
        joins_config=joins_config,
    )

    expected_results = [
        {
            "project_id": 1,
            "participant_id": 1,
            "participant_name": "Participant 1",
            "participant_role": "Developer",
        },
        {
            "project_id": 1,
            "participant_id": 2,
            "participant_name": "Participant 2",
            "participant_role": "Designer",
        },
        {
            "project_id": 2,
            "participant_id": 1,
            "participant_name": "Participant 1",
            "participant_role": "Developer",
        },
    ]

    assert len(records["data"]) == 3, "Expected three project-participant associations"
    assert (
        len(records["data"]) == records["total_count"]
    ), "Number of records should be the same in total_count and len"

    for expected, actual in zip(expected_results, records["data"]):
        assert (
            actual["id"] == expected["project_id"]
        ), f"Project ID mismatch. Expected: {expected['project_id']}, Got: {actual['id']}"
        assert (
            actual["participant_id"] == expected["participant_id"]
        ), f"Participant ID mismatch. Expected: {expected['participant_id']}, Got: {actual['participant_id']}"
        assert (
            actual["participant_name"] == expected["participant_name"]
        ), f"Participant name mismatch. Expected: {expected['participant_name']}, Got: {actual['participant_name']}"
        assert (
            actual["participant_role"] == expected["participant_role"]
        ), f"Participant role mismatch. Expected: {expected['participant_role']}, Got: {actual['participant_role']}"


@pytest.mark.asyncio
async def test_get_multi_joined_conflicting_join_parameters(async_session):
    crud = FastCRUD(ModelTest)
    with pytest.raises(ValueError) as exc_info:
        await crud.get_multi_joined(
            db=async_session,
            join_model=TierModel,
            joins_config=[
                JoinConfig(model=TierModel, join_on=TierModel.id == ModelTest.tier_id)
            ],
        )
    assert (
        "Cannot use both single join parameters and joins_config simultaneously"
        in str(exc_info.value)
    )


@pytest.mark.asyncio
async def test_get_multi_joined_missing_join_parameters(async_session):
    crud = FastCRUD(ModelTest)
    with pytest.raises(ValueError) as exc_info:
        await crud.get_multi_joined(db=async_session)
    assert "You need one of join_model or joins_config" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_multi_joined_unsupported_join_type(async_session, test_data):
    crud = FastCRUD(ModelTest)
    with pytest.raises(ValueError) as exc_info:
        await crud.get_multi_joined(
            db=async_session,
            join_model=TierModel,
            join_type="unsupported_join_type",
        )
    assert "Unsupported join type" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_multi_joined_with_joined_model_filters(
    async_session, test_data, test_data_tier
):
    for tier_data in test_data_tier:
        async_session.add(TierModel(**tier_data))
    await async_session.commit()

    for test_item in test_data:
        async_session.add(ModelTest(**test_item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)

    result = await crud.get_multi_joined(
        db=async_session,
        join_model=TierModel,
        join_filters={"name": "Premium"},
        schema_to_select=ReadSchemaTest,
        join_schema_to_select=TierSchemaTest,
        join_prefix="tier_",
        offset=0,
        limit=10,
    )

    assert (
        len(result["data"]) > 0
    ), "Expected to find at least one ModelTest record associated with the 'Premium' tier."
    for item in result["data"]:
        assert (
            item["tier_name"] == "Premium"
        ), "Expected tier_name to be 'Premium' for all fetched records."


@pytest.mark.asyncio
async def test_get_multi_joined_missing_schema_to_select(async_session, test_data):
    for test_item in test_data:
        async_session.add(ModelTest(**test_item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)
    with pytest.raises(ValueError) as exc_info:
        await crud.get_multi_joined(
            db=async_session,
            join_model=TierModel,
            return_as_model=True,
        )
    assert "schema_to_select must be provided when return_as_model is True" in str(
        exc_info.value
    )


@pytest.mark.asyncio
async def test_get_multi_joined_validation_error(
    async_session, test_data, test_model, test_data_tier
):
    for tier_data in test_data_tier:
        async_session.add(TierModel(**tier_data))
    await async_session.commit()

    for test_item in test_data:
        async_session.add(ModelTest(**test_item))
    await async_session.commit()

    invalid_test_data = {
        "name": "Extremely Long Name That Exceeds The Limits Of CustomCreateSchemaTest",
        "tier_id": 1,
    }
    async_session.add(test_model(**invalid_test_data))
    await async_session.commit()

    crud = FastCRUD(ModelTest)
    with pytest.raises(ValueError) as exc_info:
        await crud.get_multi_joined(
            db=async_session,
            join_model=TierModel,
            return_as_model=True,
            schema_to_select=CustomCreateSchemaTest,
        )

    assert "Data validation error for schema CustomCreateSchemaTest:" in str(
        exc_info.value
    )


@pytest.mark.asyncio
async def test_get_multi_joined_with_nesting(async_session, test_data, test_data_tier):
    for tier_item in test_data_tier:
        async_session.add(TierModel(**tier_item))
    await async_session.commit()

    for user_item in test_data:
        async_session.add(ModelTest(**user_item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)

    result = await crud.get_multi_joined(
        db=async_session,
        joins_config=[
            JoinConfig(
                model=TierModel,
                join_on=ModelTest.tier_id == TierModel.id,
                join_prefix="tier_",
                schema_to_select=TierSchemaTest,
                join_type="left",
            ),
            JoinConfig(
                model=CategoryModel,
                join_on=ModelTest.category_id == CategoryModel.id,
                join_prefix="category_",
                schema_to_select=CategorySchemaTest,
                join_type="left",
            ),
        ],
        schema_to_select=CreateSchemaTest,
        nest_joins=True,
        offset=0,
        limit=10,
    )

    assert result is not None, "Expected non-None result for multi joined query"
    assert "data" in result, "Result should contain 'data' key"
    assert isinstance(result["data"], list), "'data' should be a list"

    if result["data"]:
        for item in result["data"]:
            assert "tier" in item, "Nested tier data should be present under key 'tier'"
            assert (
                "category" in item
            ), "Nested category data should be present under key 'category'"
            assert isinstance(
                item["tier"], dict
            ), "Nested tier data should be a dictionary"
            assert isinstance(
                item["category"], dict
            ), "Nested category data should be a dictionary"
            assert (
                "tier_" not in item["tier"]
            ), "No prefix should be present in the nested tier keys"
            assert (
                "category_" not in item["category"]
            ), "No prefix should be present in the nested category keys"


@pytest.mark.asyncio
async def test_get_multi_joined_no_prefix_regular(
    async_session, test_data, test_data_tier
):
    for tier_item in test_data_tier:
        async_session.add(TierModel(**tier_item))
    await async_session.commit()

    for user_item in test_data:
        async_session.add(ModelTest(**user_item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)

    result = await crud.get_multi_joined(
        db=async_session,
        join_model=TierModel,
        schema_to_select=CreateSchemaTest,
        join_schema_to_select=TierSchemaTest,
        limit=10,
    )

    assert result and result["data"], "Expected data in the result."
    for item in result["data"]:
        assert "name" in item, "Expected user name in each item."
        assert "name_1" in item, "Expected tier name in each item without prefix."


@pytest.mark.asyncio
async def test_get_multi_joined_no_prefix_nested(
    async_session, test_data, test_data_tier
):
    for tier_item in test_data_tier:
        async_session.add(TierModel(**tier_item))
    await async_session.commit()

    for user_item in test_data:
        async_session.add(ModelTest(**user_item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)

    result = await crud.get_multi_joined(
        db=async_session,
        join_model=TierModel,
        schema_to_select=CreateSchemaTest,
        join_schema_to_select=TierSchemaTest,
        nest_joins=True,
        limit=10,
    )

    assert result and result["data"], "Expected data in the result."
    for item in result["data"]:
        assert "name" in item, "Expected user name in each item."
        assert (
            TierModel.__tablename__ in item
        ), f"Expected nested '{TierModel.__tablename__}' key in each item."
        assert (
            "name" in item[TierModel.__tablename__]
        ), f"Expected 'name' field inside nested '{TierModel.__tablename__}' dictionary."


@pytest.mark.asyncio
async def test_get_multi_joined_card_with_articles(async_session):
    cards = [
        Card(title="Test Card"),
        Card(title="Test Card 2"),
        Card(title="Test Card 3"),
    ]
    async_session.add_all(cards)
    await async_session.flush()

    articles = [
        Article(title="Article 1", card_id=cards[0].id),
        Article(title="Article 2", card_id=cards[1].id),
        Article(title="Article 3", card_id=cards[1].id),
    ]
    async_session.add_all(articles)
    await async_session.commit()

    card_crud = FastCRUD(Card)

    result = await card_crud.get_multi_joined(
        db=async_session,
        nest_joins=True,
        joins_config=[
            JoinConfig(
                model=Article,
                join_on=Article.card_id == Card.id,
                join_prefix="articles_",
                join_type="left",
                relationship_type="one-to-many",
            )
        ],
    )

    assert result is not None, "No data returned from the database."
    assert "data" in result, "Result should contain 'data' key."
    data = result["data"]
    assert isinstance(data, list), "Result data should be a list."
    assert len(data) == 3, "Expected three card records."

    card1 = next((c for c in data if c["id"] == cards[0].id), None)
    card2 = next((c for c in data if c["id"] == cards[1].id), None)
    card3 = next((c for c in data if c["id"] == cards[2].id), None)

    assert (
        card1 is not None and "articles" in card1
    ), "Card 1 should have nested articles."
    assert len(card1["articles"]) == 1, "Card 1 should have one article."
    assert (
        card1["articles"][0]["title"] == "Article 1"
    ), "Card 1's article title should be 'Article 1'."

    assert (
        card2 is not None and "articles" in card2
    ), "Card 2 should have nested articles."
    assert len(card2["articles"]) == 2, "Card 2 should have two articles."
    assert (
        card2["articles"][0]["title"] == "Article 2"
    ), "Card 2's first article title should be 'Article 2'."
    assert (
        card2["articles"][1]["title"] == "Article 3"
    ), "Card 2's second article title should be 'Article 3'."

    assert (
        card3 is not None and "articles" in card3
    ), "Card 3 should have nested articles."
    assert len(card3["articles"]) == 0, "Card 3 should have no articles."


@pytest.mark.asyncio
async def test_get_multi_joined_card_with_multiple_articles(async_session):
    cards = [
        Card(title="Card A"),
        Card(title="Card B"),
        Card(title="Card C"),
        Card(title="Card D"),
    ]
    async_session.add_all(cards)
    await async_session.flush()

    articles = [
        Article(title="Article 1", card_id=cards[0].id),
        Article(title="Article 2", card_id=cards[0].id),
        Article(title="Article 3", card_id=cards[1].id),
        Article(title="Article 4", card_id=cards[1].id),
        Article(title="Article 5", card_id=cards[2].id),
    ]
    async_session.add_all(articles)
    await async_session.commit()

    card_crud = FastCRUD(Card)

    result = await card_crud.get_multi_joined(
        db=async_session,
        nest_joins=True,
        joins_config=[
            JoinConfig(
                model=Article,
                join_on=Article.card_id == Card.id,
                join_prefix="articles_",
                join_type="left",
                relationship_type="one-to-many",
            )
        ],
    )

    assert result is not None, "No data returned from the database."
    assert "data" in result, "Result should contain 'data' key."
    data = result["data"]
    assert isinstance(data, list), "Result data should be a list."
    assert len(data) == 4, "Expected four card records."

    card_a = next((c for c in data if c["id"] == cards[0].id), None)
    card_b = next((c for c in data if c["id"] == cards[1].id), None)
    card_c = next((c for c in data if c["id"] == cards[2].id), None)
    card_d = next((c for c in data if c["id"] == cards[3].id), None)

    assert (
        card_a is not None and "articles" in card_a
    ), "Card A should have nested articles."
    assert len(card_a["articles"]) == 2, "Card A should have two articles."
    assert (
        card_a["articles"][0]["title"] == "Article 1"
    ), "Card A's first article title should be 'Article 1'."
    assert (
        card_a["articles"][1]["title"] == "Article 2"
    ), "Card A's second article title should be 'Article 2'."

    assert (
        card_b is not None and "articles" in card_b
    ), "Card B should have nested articles."
    assert len(card_b["articles"]) == 2, "Card B should have two articles."
    assert (
        card_b["articles"][0]["title"] == "Article 3"
    ), "Card B's first article title should be 'Article 3'."
    assert (
        card_b["articles"][1]["title"] == "Article 4"
    ), "Card B's second article title should be 'Article 4'."

    assert (
        card_c is not None and "articles" in card_c
    ), "Card C should have nested articles."
    assert len(card_c["articles"]) == 1, "Card C should have one article."
    assert (
        card_c["articles"][0]["title"] == "Article 5"
    ), "Card C's article title should be 'Article 5'."

    assert (
        card_d is not None and "articles" in card_d
    ), "Card D should have nested articles."
    assert len(card_d["articles"]) == 0, "Card D should have no articles."


@pytest.mark.asyncio
async def test_get_multi_joined_card_with_multiple_articles_as_models(async_session):
    cards = [
        Card(title="Card A"),
        Card(title="Card B"),
        Card(title="Card C"),
        Card(title="Card D"),
    ]
    async_session.add_all(cards)
    await async_session.flush()

    articles = [
        Article(title="Article 1", card_id=cards[0].id),
        Article(title="Article 2", card_id=cards[0].id),
        Article(title="Article 3", card_id=cards[1].id),
        Article(title="Article 4", card_id=cards[1].id),
        Article(title="Article 5", card_id=cards[2].id),
    ]
    async_session.add_all(articles)
    await async_session.commit()

    card_crud = FastCRUD(Card)

    result = await card_crud.get_multi_joined(
        db=async_session,
        nest_joins=True,
        return_as_model=True,
        schema_to_select=CardSchema,
        nested_schema_to_select={"articles_": ArticleSchema},
        joins_config=[
            JoinConfig(
                model=Article,
                join_on=Article.card_id == Card.id,
                join_prefix="articles_",
                join_type="left",
                relationship_type="one-to-many",
            )
        ],
    )

    assert result is not None, "No data returned from the database."
    assert "data" in result, "Result should contain 'data' key."
    data = result["data"]
    assert isinstance(data, list), "Result data should be a list."
    assert len(data) == 4, "Expected four card records."
    assert all(
        isinstance(card, CardSchema) for card in data
    ), "All items should be instances of CardSchema."

    card_a = next((c for c in data if c.id == cards[0].id), None)
    card_b = next((c for c in data if c.id == cards[1].id), None)
    card_c = next((c for c in data if c.id == cards[2].id), None)
    card_d = next((c for c in data if c.id == cards[3].id), None)

    assert card_a is not None and hasattr(
        card_a, "articles"
    ), "Card A should have nested articles."
    assert len(card_a.articles) == 2, "Card A should have two articles."
    assert (
        card_a.articles[0].title == "Article 1"
    ), "Card A's first article title should be 'Article 1'."
    assert (
        card_a.articles[1].title == "Article 2"
    ), "Card A's second article title should be 'Article 2'."
    assert all(
        isinstance(article, ArticleSchema) for article in card_a.articles
    ), "All articles in Card A should be instances of ArticleSchema."

    assert card_b is not None and hasattr(
        card_b, "articles"
    ), "Card B should have nested articles."
    assert len(card_b.articles) == 2, "Card B should have two articles."
    assert (
        card_b.articles[0].title == "Article 3"
    ), "Card B's first article title should be 'Article 3'."
    assert (
        card_b.articles[1].title == "Article 4"
    ), "Card B's second article title should be 'Article 4'."
    assert all(
        isinstance(article, ArticleSchema) for article in card_b.articles
    ), "All articles in Card B should be instances of ArticleSchema."

    assert card_c is not None and hasattr(
        card_c, "articles"
    ), "Card C should have nested articles."
    assert len(card_c.articles) == 1, "Card C should have one article."
    assert (
        card_c.articles[0].title == "Article 5"
    ), "Card C's article title should be 'Article 5'."
    assert all(
        isinstance(article, ArticleSchema) for article in card_c.articles
    ), "All articles in Card C should be instances of ArticleSchema."

    assert card_d is not None and hasattr(
        card_d, "articles"
    ), "Card D should have nested articles."
    assert len(card_d.articles) == 0, "Card D should have no articles."

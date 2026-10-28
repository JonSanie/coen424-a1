from __future__ import annotations

import os
from typing import Any, cast

import redis
from redis.exceptions import ResponseError
from redis.commands.search.field import Field, NumericField, TagField, TextField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.commands.search.result import Result


INDEX_NAME = "idx:prizes"
KEY_PREFIX = "prizes:"


def create_prize_index(client: redis.Redis) -> None:
    schema: list[Field] = [
        NumericField("$.year", as_name="year"),
        TagField("$.category", as_name="category"),
        TextField("$.laureates[*].motivation", as_name="motivation"),
        TextField("$.laureates[*].firstname", as_name="firstname"),
        TextField("$.laureates[*].surname", as_name="surname"),
    ]
    index = client.ft(INDEX_NAME)

    try:
        index.info()
    except ResponseError as error:
        if "INDEX_NOT_FOUND" not in str(error) and "Unknown Index name" not in str(error):
            raise
        index.create_index(
            schema,
            definition=IndexDefinition(
                prefix=[KEY_PREFIX],
                index_type=IndexType.JSON,
            ),
        )
        return

    index.dropindex(delete_documents=False)
    index.create_index(
        schema,
        definition=IndexDefinition(
            prefix=[KEY_PREFIX],
            index_type=IndexType.JSON,
        ),
    )


def _json_document(client: redis.Redis, key: str) -> dict[str, Any]:
    document: Any = client.json().get(key)
    if not isinstance(document, dict):
        raise TypeError(f"Redis document {key!r} is not a JSON object")
    return document


def count_laureates_by_category_and_year(
    client: redis.Redis,
    category: str,
    start_year: int,
    end_year: int,
) -> int:
    if not 2013 <= start_year <= end_year <= 2023:
        raise ValueError("The year range must be within 2013 through 2023.")

    query = Query(
        f"@category:{{{category}}} @year:[{start_year} {end_year}]"
    ).no_content()
    results = cast(Result, client.ft(INDEX_NAME).search(query))
    return sum(
        len(_json_document(client, result.id).get("laureates", []))
        for result in results.docs
    )


def count_laureates_by_motivation_keyword(
    client: redis.Redis,
    keyword: str,
) -> int:
    query = Query(f"@motivation:({keyword})").no_content()
    results = cast(Result, client.ft(INDEX_NAME).search(query))
    return sum(
        sum(
            1
            for laureate in _json_document(client, result.id).get("laureates", [])
            if keyword.casefold()
            in laureate.get("motivation", "").casefold()
        )
        for result in results.docs
    )


def find_laureate(
    client: redis.Redis,
    firstname: str,
    surname: str,
) -> list[dict[str, str]]:
    query = Query(f"@firstname:({firstname}) @surname:({surname})")
    results = cast(Result, client.ft(INDEX_NAME).search(query))
    matches: list[dict[str, str]] = []

    for result in results.docs:
        prize = _json_document(client, result.id)
        for laureate in prize.get("laureates", []):
            if (
                laureate.get("firstname") == firstname
                and laureate.get("surname") == surname
            ):
                matches.append(
                    {
                        "year": prize["year"],
                        "category": prize["category"],
                        "motivation": laureate["motivation"],
                    }
                )
    return matches


def main() -> None:
    host = os.environ.get("REDIS_HOST")
    port_text = os.environ.get("REDIS_PORT")
    password = os.environ.get("REDIS_PASSWORD")
    if not host or not port_text or not password:
        raise RuntimeError(
            "REDIS_HOST, REDIS_PORT, and REDIS_PASSWORD environment variables "
            "must be set."
        )

    client = redis.Redis(
        host=host,
        port=int(port_text),
        password=password,
        decode_responses=True,
    )
    client.ping()
    create_prize_index(client)

    category_count = count_laureates_by_category_and_year(
        client, "physics", 2013, 2023
    )
    keyword_count = count_laureates_by_motivation_keyword(client, "quantum")
    laureate_matches = find_laureate(client, "Arthur", "Ashkin")

    print(f"Physics laureates from 2013 through 2023: {category_count}")
    print(f"Laureates with 'quantum' in their motivation: {keyword_count}")
    print("Arthur Ashkin matches:")
    for match in laureate_matches:
        print(f"  {match}")


if __name__ == "__main__":
    main()
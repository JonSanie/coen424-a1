import json
import os
from pathlib import Path

import redis


MIN_YEAR = 2013
MAX_YEAR = 2023


def main() -> None:
    json_path = Path(__file__).with_name("prize.json")
    with json_path.open(encoding="utf-8") as file:
        prize_data = json.load(file)

    filtered_prizes = [
        {**prize, "year": int(prize["year"])}
        for prize in prize_data["prizes"]
        if MIN_YEAR <= int(prize["year"]) <= MAX_YEAR
    ]

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

    for prize in filtered_prizes:
        prize_id = f"{prize['year']}-{prize['category']}"
        client.json().set(f"prizes:{prize_id}", "$", prize)

    print(f"Stored {len(filtered_prizes)} prizes in Redis.")


if __name__ == "__main__":
    main()
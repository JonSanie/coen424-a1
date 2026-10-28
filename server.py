# pyright: reportAttributeAccessIssue=false

from concurrent import futures
import os

import grpc
import redis

import nobel_pb2
import nobel_pb2_grpc
from task1_queries import (
    count_laureates_by_category_and_year,
    count_laureates_by_motivation_keyword,
    create_prize_index,
    find_laureate,
)


def create_redis_client() -> redis.Redis:
    host = os.environ.get("REDIS_HOST")
    port_text = os.environ.get("REDIS_PORT")
    password = os.environ.get("REDIS_PASSWORD")

    if not host or not port_text or not password:
        raise RuntimeError(
            "REDIS_HOST, REDIS_PORT, and REDIS_PASSWORD environment variables "
            "must be set."
        )

    try:
        port = int(port_text)
    except ValueError as error:
        raise RuntimeError("REDIS_PORT must be an integer.") from error

    return redis.Redis(
        host=host,
        port=port,
        password=password,
        socket_connect_timeout=10,
        socket_timeout=10,
        decode_responses=True,
    )


class NobelService(nobel_pb2_grpc.NobelServiceServicer):
    def __init__(self, client: redis.Redis) -> None:
        self.client = client

    def GetLaureatesByCategory(
        self,
        request: nobel_pb2.CategoryRequest,
        context: grpc.ServicerContext,
    ) -> nobel_pb2.CountResponse:
        try:
            count = count_laureates_by_category_and_year(
                self.client,
                request.category,
                request.start_year,
                request.end_year,
            )
        except ValueError as error:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(error))
        return nobel_pb2.CountResponse(count=count)

    def GetLaureatesByKeyword(
        self,
        request: nobel_pb2.KeywordRequest,
        context: grpc.ServicerContext,
    ) -> nobel_pb2.CountResponse:
        if not request.keyword.strip():
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "keyword is required.")
        count = count_laureates_by_motivation_keyword(
            self.client,
            request.keyword,
        )
        return nobel_pb2.CountResponse(count=count)

    def GetLaureateDetails(
        self,
        request: nobel_pb2.LaureateDetailsRequest,
        context: grpc.ServicerContext,
    ) -> nobel_pb2.LaureateDetailsResponse:
        if not request.firstname.strip() or not request.lastname.strip():
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "firstname and lastname are required.",
            )

        matches = find_laureate(
            self.client,
            request.firstname,
            request.lastname,
        )
        return nobel_pb2.LaureateDetailsResponse(
            laureates=[
                nobel_pb2.LaureateDetails(
                    year=str(match["year"]),
                    category=match["category"],
                    motivation=match["motivation"],
                )
                for match in matches
            ]
        )


def serve() -> None:
    port_text = os.environ.get("PORT", "8080")
    try:
        port = int(port_text)
    except ValueError as error:
        raise RuntimeError("PORT must be an integer.") from error

    client = create_redis_client()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    nobel_pb2_grpc.add_NobelServiceServicer_to_server(
        NobelService(client),
        server,
    )
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"NobelService listening on port {port}", flush=True)

    print("Connecting to Redis...", flush=True)
    client.ping()
    print("Connected to Redis.", flush=True)
    create_prize_index(client)
    print("Redis index is ready.", flush=True)
    print("NobelService is ready for RPCs.", flush=True)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
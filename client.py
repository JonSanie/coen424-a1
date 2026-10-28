# pyright: reportAttributeAccessIssue=false

import csv
import os
import time

import grpc

import nobel_pb2
import nobel_pb2_grpc


SERVER_ADDRESS = os.environ.get(
    "GRPC_SERVER_ADDRESS",
    "https://nobel-service-339047474343.us-east1.run.app:443",
)
ITERATIONS = 100
OUTPUT_FILE = "latencies.csv"


def measure_latencies(stub: nobel_pb2_grpc.NobelServiceStub) -> tuple[
    list[float], list[float], list[float]
]:
    query_1_latencies: list[float] = []
    query_2_latencies: list[float] = []
    query_3_latencies: list[float] = []

    for _ in range(ITERATIONS):
        start = time.perf_counter()
        stub.GetLaureatesByCategory(
            nobel_pb2.CategoryRequest(
                category="physics",
                start_year=2013,
                end_year=2023,
            )
        )
        query_1_latencies.append((time.perf_counter() - start) * 1000)

    for _ in range(ITERATIONS):
        start = time.perf_counter()
        stub.GetLaureatesByKeyword(
            nobel_pb2.KeywordRequest(keyword="quantum")
        )
        query_2_latencies.append((time.perf_counter() - start) * 1000)

    for _ in range(ITERATIONS):
        start = time.perf_counter()
        stub.GetLaureateDetails(
            nobel_pb2.LaureateDetailsRequest(
                firstname="Arthur",
                lastname="Ashkin",
            )
        )
        query_3_latencies.append((time.perf_counter() - start) * 1000)

    return query_1_latencies, query_2_latencies, query_3_latencies


def save_latencies(
    query_1_latencies: list[float],
    query_2_latencies: list[float],
    query_3_latencies: list[float],
) -> None:
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["iteration", "query_1_ms", "query_2_ms", "query_3_ms"])
        for index in range(ITERATIONS):
            writer.writerow(
                [
                    index + 1,
                    query_1_latencies[index],
                    query_2_latencies[index],
                    query_3_latencies[index],
                ]
            )


def main() -> None:
    target = SERVER_ADDRESS.removeprefix("https://")
    credentials = grpc.ssl_channel_credentials()
    with grpc.secure_channel(target, credentials) as channel:
        stub = nobel_pb2_grpc.NobelServiceStub(channel)
        latencies = measure_latencies(stub)

    save_latencies(*latencies)
    print(f"Saved {ITERATIONS} latencies for each query to {OUTPUT_FILE}.")


if __name__ == "__main__":
    main()
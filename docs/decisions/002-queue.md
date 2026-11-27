# ADR 002: SQS-compatible local queue
ElasticMQ and Boto3 keep the project free and separate ingestion from processing. Alternative: synchronous processing, simpler but no retry isolation. Trade-off: local emulator is not AWS and in-memory queue loses data on container removal. At-least-once delivery requires idempotency.

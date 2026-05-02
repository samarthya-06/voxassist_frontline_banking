import asyncio
import random


async def seed() -> None:
    from backend.app.services.repositories import repository

    await repository.ensure_database()

    data = [
        ("Marathi", "Card Support", "negative"),
        ("Gujarati", "FD Services", "positive"),
        ("Hindi", "KYC Update", "neutral"),
        ("Tamil", "Loan Enquiry", "positive"),
        ("Kannada", "Account Opening", "neutral"),
        ("Bengali", "Card Support", "negative"),
        ("Hindi", "FD Services", "positive"),
        ("Marathi", "Loan Enquiry", "negative"),
        ("Gujarati", "KYC Update", "positive"),
        ("Telugu", "Account Opening", "neutral"),
    ]

    for i, (language, service, sentiment) in enumerate(data):
        session_id = f"sess-{i:03d}"
        await repository.save_summary(
            session_id,
            {
                "type": "summary",
                "service": service,
                "status": "Escalated" if sentiment == "negative" and i % 2 == 0 else "Completed",
                "language": language,
                "duration": f"0{random.randint(3, 9)}:{random.randint(10, 59)}",
                "sentiment": sentiment,
                "entities": {"customerName": f"Demo Customer {i + 1}", "accountType": "Savings"},
                "english": [
                    f"Customer inquired about {service}",
                    "Staff resolved the query",
                    "Session concluded",
                ],
                "customerLanguage": [
                    "Customer asked about the service",
                    "Staff resolved the issue",
                ],
                "formsFilled": ["KYC Form"] if "KYC" in service else [],
                "complianceFlags": 1 if sentiment == "negative" and i % 3 == 0 else 0,
            },
        )

    print("Seeded 10 demo sessions successfully.")


if __name__ == "__main__":
    asyncio.run(seed())

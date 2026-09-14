from __future__ import annotations

import argparse
import asyncio

from app.main import app


async def run(force: bool) -> None:
    seeded = await app.state.service.initialize(force=force)
    message = "Demo data reset complete." if force else ("Seed data created." if seeded else "Existing data preserved.")
    print(message)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="자립동행 데모 JSON 데이터 초기화")
    parser.add_argument("--reset", action="store_true", help="기존 데이터를 백업하고 초기 상태로 되돌립니다.")
    args = parser.parse_args()
    asyncio.run(run(args.reset))

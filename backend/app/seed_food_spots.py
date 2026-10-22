import json
from pathlib import Path

from sqlalchemy import select

from app.database import create_tables, SessionLocal
from app.models import FoodSpot


DATA_FILE = Path(__file__).parent / "data" / "food_spots.json"


def seed_food_spots():
    create_tables()

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        city_blocks = json.load(file)  # list of {city, top_food_tourism_spots}

    with SessionLocal() as db:
        inserted = 0

        for block in city_blocks:
            city_name = block["city"]
            for spot in block.get("top_food_tourism_spots", []):
                # Skip if this (city, spot_id) pair already exists.
                existing = db.scalar(
                    select(FoodSpot).where(
                        FoodSpot.city == city_name,
                        FoodSpot.spot_id == spot["spot_id"],
                    )
                )
                if existing:
                    continue

                db.add(
                    FoodSpot(
                        spot_id=spot["spot_id"],
                        city=city_name,
                        tourist_attraction=spot.get("tourist_attraction", ""),
                        famous_food_spot=spot.get("famous_food_spot", ""),
                        speciality_dish=spot.get("speciality_dish", ""),
                        rating_as_per_google=spot.get("rating_as_per_google"),
                        description=spot.get("description"),
                        google_maps_link=spot.get("google_maps_link"),
                    )
                )
                inserted += 1

        db.commit()

    print(f"Food spots inserted: {inserted}")


if __name__ == "__main__":
    seed_food_spots()
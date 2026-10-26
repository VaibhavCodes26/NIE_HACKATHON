
import json
from pathlib import Path

from sqlalchemy import select

from app.database import create_tables, SessionLocal
from app.models import FoodSpot


DATA_FILE = Path(__file__).parent / "data" / "food_spots.json"


def seed_food_spots():
    create_tables()

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        city_blocks = json.load(file)

    inserted = 0
    updated = 0

    image_fields = (
        "image_url",
        "image_source",
        "image_source_url",
        "image_credit",
        "image_license",
        "image_alt",
    )

    with SessionLocal() as db:
        for block in city_blocks:
            city_name = block["city"]

            for spot in block.get("top_food_tourism_spots", []):
                spot_id = spot["spot_id"]

                existing = db.scalar(
                    select(FoodSpot).where(
                        FoodSpot.city == city_name,
                        FoodSpot.spot_id == spot_id,
                    )
                )

                values = {
                    "tourist_attraction": spot.get(
                        "tourist_attraction", ""
                    ),
                    "famous_food_spot": spot.get(
                        "famous_food_spot", ""
                    ),
                    "speciality_dish": spot.get(
                        "speciality_dish", ""
                    ),
                    "rating_as_per_google": spot.get(
                        "rating_as_per_google"
                    ),
                    "description": spot.get("description"),
                    "google_maps_link": spot.get(
                        "google_maps_link"
                    ),
                }

                # Include image metadata when present in JSON.
                for field in image_fields:
                    if field in spot:
                        values[field] = spot[field]

                if existing:
                    # Update the existing database record.
                    for field, value in values.items():
                        setattr(existing, field, value)

                    updated += 1
                else:
                    # Insert a new record.
                    db.add(
                        FoodSpot(
                            spot_id=spot_id,
                            city=city_name,
                            **values,
                        )
                    )
                    inserted += 1

        db.commit()

    print(f"Food spots inserted: {inserted}")
    print(f"Food spots updated: {updated}")


if __name__ == "__main__":
    seed_food_spots()

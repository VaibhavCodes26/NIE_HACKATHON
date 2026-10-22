
"""SQLAlchemy database models for NammaPrayana."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Column,
    UniqueConstraint,
)
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Destination(Base):
    """A selectable Karnataka destination from PlanJourney.jsx."""

    __tablename__ = "destinations"

    # Keep these IDs identical to the frontend destination IDs.
    id: Mapped[str] = mapped_column(String(60), primary_key=True)

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    attractions: Mapped[list["Attraction"]] = relationship(
        back_populates="destination",
        cascade="all, delete-orphan",
        order_by="Attraction.visit_order",
    )

    def __repr__(self) -> str:
        return f"Destination(id={self.id!r}, name={self.name!r})"


class Attraction(Base):
    """A curated tourist attraction associated with a destination."""

    __tablename__ = "attractions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    destination_id: Mapped[str] = mapped_column(
        String(60),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Example: "09:00–11:00". This is a suggested visit window,
    # not a verified opening-hours claim.
    suggested_time: Mapped[str] = mapped_column(
        String(60),
        default="Time to be planned",
        nullable=False,
    )

    # Example: ["Heritage & culture", "Tourist attractions"]
    interest_tags: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    estimated_duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    visit_order: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    is_must_visit: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Use "curated_reference" only for reviewed reference data.
    # Unverified information must be labelled accordingly.
    source_status: Mapped[str] = mapped_column(
        String(40),
        default="needs_verification",
        nullable=False,
    )

    source_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    destination: Mapped["Destination"] = relationship(
        back_populates="attractions",
    )

    __table_args__ = (
        Index(
            "ix_attractions_destination_visit_order",
            "destination_id",
            "visit_order",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"Attraction(id={self.id!r}, "
            f"name={self.name!r}, "
            f"destination_id={self.destination_id!r})"
        )

class FoodSpot(Base):
    __tablename__ = "food_spots"
    __table_args__ = (
        # Each city reuses spot_ids 1-8, so we need a composite unique key.
        UniqueConstraint("city", "spot_id", name="uq_food_spots_city_spot"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    spot_id = Column(Integer, nullable=False, index=True)
    city = Column(String(100), nullable=False, index=True)

    tourist_attraction = Column(String(200), nullable=False)
    famous_food_spot = Column(String(200), nullable=False)
    speciality_dish = Column(String(300), nullable=False)

    rating_as_per_google = Column(String(30), nullable=True)
    description = Column(Text, nullable=True)
    google_maps_link = Column(Text, nullable=True)
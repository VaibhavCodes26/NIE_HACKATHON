
"""SQLAlchemy database models for NammaPrayana."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
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

    # Suggested visit window, not verified opening hours.
    suggested_time: Mapped[str] = mapped_column(
        String(60),
        default="Time to be planned",
        nullable=False,
    )

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
    """A local food spot with optional image and attribution metadata."""

    __tablename__ = "food_spots"

    __table_args__ = (
        # Spot IDs can repeat across cities.
        UniqueConstraint(
            "city",
            "spot_id",
            name="uq_food_spots_city_spot",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    spot_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    tourist_attraction: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    famous_food_spot: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    speciality_dish: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    rating_as_per_google: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    google_maps_link: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Optional food photography.
    image_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Image source and licensing attribution.
    image_source: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    image_source_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    image_credit: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    image_license: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    image_alt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"FoodSpot(id={self.id!r}, "
            f"city={self.city!r}, "
            f"name={self.famous_food_spot!r})"
        )


class User(Base):
    """Authenticated NammaPrayana user account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    username: Mapped[str] = mapped_column(
        String(80),
        unique=True,
        nullable=False,
        index=True,
    )

    # Nullable for Google-only accounts.
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Stable Google subject identifier.
    google_sub: Mapped[str | None] = mapped_column(
        String(200),
        unique=True,
        nullable=True,
        index=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(254),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    saved_itineraries: Mapped[list["SavedItinerary"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, username={self.username!r})"


class UserSession(Base):
    """Server-side session record for an authenticated user."""

    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Opaque, cryptographically random token stored in an HttpOnly cookie.
    token: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="sessions")

    def is_expired(self) -> bool:
        expires = self.expires_at

        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)

        return datetime.now(timezone.utc) >= expires

    def __repr__(self) -> str:
        return f"UserSession(id={self.id!r}, user_id={self.user_id!r})"


class SavedItinerary(Base):
    """A complete generated itinerary saved by an authenticated user."""

    __tablename__ = "saved_itineraries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(400), nullable=False)

    trip_config: Mapped[dict] = mapped_column(JSON, nullable=False)

    itinerary_payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    destinations: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    selected_attraction_ids: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    start_date: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    end_date: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    traveller_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    total_budget: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    travel_style: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    duration_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship(back_populates="saved_itineraries")

    __table_args__ = (
        Index(
            "ix_saved_itineraries_user_id_created_at",
            "user_id",
            "created_at",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"SavedItinerary(id={self.id!r}, "
            f"user_id={self.user_id!r}, "
            f"title={self.title!r})"
        )

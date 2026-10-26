
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


# ---------------------------------------------------------------------------
# Authentication models
# ---------------------------------------------------------------------------

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

    # Stable Google subject identifier (sub claim). Nullable for password accounts.
    google_sub: Mapped[str | None] = mapped_column(
        String(200),
        unique=True,
        nullable=True,
        index=True,
    )

    # Optional email — stored only when provided by Google; never used as identity key.
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)

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

    # Opaque, cryptographically random token stored in the HttpOnly cookie.
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

    # Human-readable trip title (e.g. "Your Karnataka Journey: Bengaluru → Mysuru")
    title: Mapped[str] = mapped_column(String(400), nullable=False)

    # Original Plan Your Journey configuration as JSON
    trip_config: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Complete AI-generated itinerary payload (days, warnings, gati, etc.)
    itinerary_payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Ordered list of destination names for quick display
    destinations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Selected attraction IDs
    selected_attraction_ids: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )

    start_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(20), nullable=True)

    traveller_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_budget: Mapped[int | None] = mapped_column(Integer, nullable=True)
    travel_style: Mapped[str | None] = mapped_column(String(40), nullable=True)

    # ISO-format number of trip days for quick display
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

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
        Index("ix_saved_itineraries_user_id_created_at", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"SavedItinerary(id={self.id!r}, user_id={self.user_id!r}, title={self.title!r})"
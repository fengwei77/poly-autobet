"""
Data: SQLAlchemy 2.0 async ORM models for markets, trades, weather, and analysis.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, Integer, Boolean, DateTime, Text, JSON, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Market(Base):
    """Polymarket weather market snapshot."""
    __tablename__ = "markets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    condition_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    question: Mapped[str] = mapped_column(Text)
    market_slug: Mapped[str] = mapped_column(String(256), default="")
    category: Mapped[str] = mapped_column(String(64), default="weather")  # temperature, precipitation, etc.
    city: Mapped[str] = mapped_column(String(64), index=True, default="")
    tokens: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # YES/NO token IDs

    # Pricing
    yes_price: Mapped[float] = mapped_column(Float, default=0.0)
    no_price: Mapped[float] = mapped_column(Float, default=0.0)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    liquidity: Mapped[float] = mapped_column(Float, default=0.0)

    # Timing
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Market {self.condition_id[:8]}... {self.city} yes={self.yes_price:.2f}>"


class WeatherForecast(Base):
    """Weather forecast data point from an API source."""
    __tablename__ = "weather_forecasts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    city: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(32))  # noaa, openweathermap, open_meteo
    forecast_date: Mapped[datetime] = mapped_column(DateTime, index=True)

    # Weather data
    temp_high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temp_low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    precipitation_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wind_speed_kmh: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    humidity_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(String(256), default="")

    # Quality
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # API-reported confidence

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AnalysisResult(Base):
    """AI analysis result for a market opportunity."""
    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    market_condition_id: Mapped[str] = mapped_column(String(128), index=True)
    city: Mapped[str] = mapped_column(String(64))

    # Analysis output
    forecast_probability: Mapped[float] = mapped_column(Float)
    market_price: Mapped[float] = mapped_column(Float)
    edge: Mapped[float] = mapped_column(Float)
    confidence: Mapped[int] = mapped_column(Integer)
    signal: Mapped[str] = mapped_column(String(8))  # BUY, SELL, HOLD
    reasoning: Mapped[str] = mapped_column(Text, default="")
    risk_factors: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Kelly
    kelly_fraction: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    suggested_size_usdc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Trade(Base):
    """Executed trade record (paper or live)."""
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    market_condition_id: Mapped[str] = mapped_column(String(128), index=True)
    order_id: Mapped[str] = mapped_column(String(128), default="")

    # Trade details
    side: Mapped[str] = mapped_column(String(8))  # BUY, SELL
    token_id: Mapped[str] = mapped_column(String(128), default="")
    price: Mapped[float] = mapped_column(Float)
    size: Mapped[float] = mapped_column(Float)
    amount_usdc: Mapped[float] = mapped_column(Float)

    # Execution
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending, filled, cancelled, failed
    fill_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_paper: Mapped[bool] = mapped_column(Boolean, default=True)

    # P&L (filled after resolution)
    pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)

    # Metadata
    node_id: Mapped[str] = mapped_column(String(32), default="brain")  # Which node executed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        mode = "📝" if self.is_paper else "💰"
        return f"<Trade {mode} {self.side} ${self.amount_usdc:.2f} @ {self.price:.4f}>"


class DailyPnL(Base):
    """Daily P&L summary."""
    __tablename__ = "daily_pnl"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), unique=True, index=True)  # YYYY-MM-DD
    total_invested: Mapped[float] = mapped_column(Float, default=0.0)
    total_returned: Mapped[float] = mapped_column(Float, default=0.0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    trade_count: Mapped[int] = mapped_column(Integer, default=0)
    win_count: Mapped[int] = mapped_column(Integer, default=0)
    loss_count: Mapped[int] = mapped_column(Integer, default=0)
class CityAlias(Base):
    """Mapping of aliases, abbreviations, and misspellings to standardized city IDs."""
    __tablename__ = "city_aliases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    alias: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # e.g., 'NYC', 'SFO', 'Philly'
    city_id: Mapped[str] = mapped_column(String(64), index=True)            # e.g., 'new_york'
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)       # Whether AI or user verified this
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

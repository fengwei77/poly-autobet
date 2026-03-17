"""Initial migration - create all tables

Revision ID: 001_initial
Revises:
Create Date: 2026-03-17

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Markets table
    op.create_table(
        'markets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('condition_id', sa.String(128), nullable=False),
        sa.Column('question', sa.Text(), nullable=True),
        sa.Column('market_slug', sa.String(256), nullable=True),
        sa.Column('category', sa.String(64), nullable=True),
        sa.Column('city', sa.String(64), nullable=True),
        sa.Column('tokens', sa.JSON(), nullable=True),
        sa.Column('yes_price', sa.Float(), nullable=True),
        sa.Column('no_price', sa.Float(), nullable=True),
        sa.Column('volume', sa.Float(), nullable=True),
        sa.Column('liquidity', sa.Float(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('condition_id')
    )
    op.create_index('ix_markets_condition_id', 'markets', ['condition_id'])
    op.create_index('ix_markets_city', 'markets', ['city'])

    # Weather forecasts table
    op.create_table(
        'weather_forecasts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('city', sa.String(64), nullable=True),
        sa.Column('source', sa.String(32), nullable=True),
        sa.Column('forecast_date', sa.DateTime(), nullable=True),
        sa.Column('temp_high', sa.Float(), nullable=True),
        sa.Column('temp_low', sa.Float(), nullable=True),
        sa.Column('precipitation_mm', sa.Float(), nullable=True),
        sa.Column('wind_speed_kmh', sa.Float(), nullable=True),
        sa.Column('humidity_pct', sa.Float(), nullable=True),
        sa.Column('description', sa.String(256), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_weather_forecasts_city', 'weather_forecasts', ['city'])
    op.create_index('ix_weather_forecasts_forecast_date', 'weather_forecasts', ['forecast_date'])

    # Analysis results table
    op.create_table(
        'analysis_results',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('market_condition_id', sa.String(128), nullable=True),
        sa.Column('city', sa.String(64), nullable=True),
        sa.Column('forecast_probability', sa.Float(), nullable=True),
        sa.Column('market_price', sa.Float(), nullable=True),
        sa.Column('edge', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Integer(), nullable=True),
        sa.Column('signal', sa.String(8), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('risk_factors', sa.JSON(), nullable=True),
        sa.Column('kelly_fraction', sa.Float(), nullable=True),
        sa.Column('suggested_size_usdc', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_analysis_results_market_condition_id', 'analysis_results', ['market_condition_id'])

    # Trades table
    op.create_table(
        'trades',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('market_condition_id', sa.String(128), nullable=True),
        sa.Column('order_id', sa.String(128), nullable=True),
        sa.Column('side', sa.String(8), nullable=True),
        sa.Column('token_id', sa.String(128), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('size', sa.Float(), nullable=True),
        sa.Column('amount_usdc', sa.Float(), nullable=True),
        sa.Column('status', sa.String(16), nullable=True),
        sa.Column('fill_price', sa.Float(), nullable=True),
        sa.Column('is_paper', sa.Boolean(), nullable=True),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=True),
        sa.Column('node_id', sa.String(32), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_trades_market_condition_id', 'trades', ['market_condition_id'])

    # Daily PnL table
    op.create_table(
        'daily_pnl',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('date', sa.String(10), nullable=True),
        sa.Column('total_invested', sa.Float(), nullable=True),
        sa.Column('total_returned', sa.Float(), nullable=True),
        sa.Column('realized_pnl', sa.Float(), nullable=True),
        sa.Column('trade_count', sa.Integer(), nullable=True),
        sa.Column('win_count', sa.Integer(), nullable=True),
        sa.Column('loss_count', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date')
    )
    op.create_index('ix_daily_pnl_date', 'daily_pnl', ['date'])

    # City aliases table
    op.create_table(
        'city_aliases',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('alias', sa.String(64), nullable=True),
        sa.Column('city_id', sa.String(64), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('alias')
    )
    op.create_index('ix_city_aliases_alias', 'city_aliases', ['alias'])
    op.create_index('ix_city_aliases_city_id', 'city_aliases', ['city_id'])


def downgrade() -> None:
    op.drop_table('city_aliases')
    op.drop_table('daily_pnl')
    op.drop_table('trades')
    op.drop_table('analysis_results')
    op.drop_table('weather_forecasts')
    op.drop_table('markets')

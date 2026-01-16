"""Add Azure AD SSO fields to users table

Revision ID: add_azure_ad_sso
Revises: 
Create Date: 2026-01-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_azure_ad_sso'
down_revision = None  # Update this to the previous migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add Azure AD SSO fields to users table."""
    # Add azure_ad_id column (Microsoft user ID)
    op.add_column(
        'users',
        sa.Column('azure_ad_id', sa.String(255), nullable=True, unique=True)
    )
    
    # Add oauth_provider column ('azure_ad', 'local', etc.)
    op.add_column(
        'users',
        sa.Column('oauth_provider', sa.String(50), nullable=True)
    )
    
    # Create unique index on azure_ad_id for faster lookups
    op.create_index(
        'ix_users_azure_ad_id',
        'users',
        ['azure_ad_id'],
        unique=True
    )


def downgrade() -> None:
    """Remove Azure AD SSO fields from users table."""
    op.drop_index('ix_users_azure_ad_id', table_name='users')
    op.drop_column('users', 'oauth_provider')
    op.drop_column('users', 'azure_ad_id')

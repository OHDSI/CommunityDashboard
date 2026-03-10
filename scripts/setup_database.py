#!/usr/bin/env python3
"""
Setup PostgreSQL database for OHDSI Community Intelligence Platform.
Creates tables and initial configuration.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import asyncpg
from backend.app.config import settings

async def setup_database():
    """Create database tables and initial setup."""
    print("Setting up PostgreSQL database...")
    
    # Connect to database
    conn = await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DB
    )
    
    try:
        # Create users table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                organization VARCHAR(255),
                role VARCHAR(50) DEFAULT 'explorer',
                created_at TIMESTAMP DEFAULT NOW(),
                last_login TIMESTAMP
            )
        """)
        print("✓ Created users table")
        
        # Create API keys table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                key_hash VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(255),
                permissions JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT NOW(),
                last_used TIMESTAMP
            )
        """)
        print("✓ Created api_keys table")
        
        # Create user preferences table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                preferences JSONB DEFAULT '{}',
                saved_searches JSONB DEFAULT '[]',
                bookmarks JSONB DEFAULT '[]',
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        print("✓ Created user_preferences table")
        
        # Create review_logs table for audit trail
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS review_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                content_id VARCHAR(255) NOT NULL,
                reviewer_id UUID REFERENCES users(id),
                action VARCHAR(50) NOT NULL,
                categories JSONB,
                reason TEXT,
                ml_score FLOAT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        print("✓ Created review_logs table")
        
        # Create indices
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_review_logs_content ON review_logs(content_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_review_logs_reviewer ON review_logs(reviewer_id)")
        print("✓ Created database indices")
        
        # Create default admin user (for development)
        if os.getenv("ENVIRONMENT", "development") == "development":
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            
            admin_email = os.getenv("ADMIN_EMAIL", "admin@ohdsi.org")
            admin_password = pwd_context.hash(os.getenv("ADMIN_PASSWORD", "changeme"))

            await conn.execute("""
                INSERT INTO users (email, password_hash, full_name, organization, role)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (email) DO NOTHING
            """, admin_email, admin_password, "Admin User", "OHDSI", "admin")

            print("✓ Created default admin user")
        
        print("\n✅ PostgreSQL database setup complete!")
        
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(setup_database())
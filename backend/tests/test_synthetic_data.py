"""
Test data loader: Populate database with synthetic Kenya-wide data.
Creates 47 counties with all required fields, synthetic barometer readings.

Run with: python tests/test_synthetic_data.py
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from geoalchemy2 import Geometry
import random

from core.config import settings
from models.orm import Base, County, BarometerReading, User
from core.security import hash_password, hash_device_id


# Kenya county data (simplified - in production, load from GIS file)
COUNTIES_DATA = [
    ("01", "Mombasa", -4.0, 39.67, is_urban=True),
    ("02", "Kwale", -4.25, 39.5),
    ("03", "Kilifi", -3.3, 39.9),
    ("04", "Nairobi", -1.29, 36.82, is_urban=True),
    ("05", "Lamu", -2.25, 40.9),
    ("06", "Taita-Taveta", -3.4, 38.25),
    ("07", "Garissa", -0.45, 39.65),
    ("08", "Wajir", 1.75, 40.05),
    ("09", "Mandera", 3.75, 41.05),
    ("10", "Marsabit", 2.7, 37.9),
    ("11", "Isiolo", 0.35, 37.6),
    ("12", "Meru", -0.05, 37.65, is_urban=True),
    ("13", "Tharaka-Nithi", 0.3, 37.75),
    ("14", "Embu", -0.5, 37.45),
    ("15", "Kitui", -2.25, 38.25),
    ("16", "Makueni", -2.75, 37.85),
    ("17", "Kiambu", -1.15, 36.8, is_urban=True),
    ("18", "Kajiado", -1.95, 36.75),
    ("19", "Kericho", -0.35, 35.3),
    ("20", "Bomet", -0.8, 35.3),
    ("21", "Kakamega", 0.35, 34.8),
    ("22", "Vihiga", 0.65, 34.75),
    ("23", "Kisii", -0.7, 34.8),
    ("24", "Nyamira", -0.6, 34.45),
    ("25", "Narok", -1.4, 35.4),
    ("26", "Trans-Nzoia", 1.1, 35.05),
    ("27", "Uasin-Gishu", 0.95, 34.95, is_urban=True),
    ("28", "Elgeyo-Marakwet", 1.2, 35.3),
    ("29", "Nandi", 0.5, 35.15),
    ("30", "Kisumu", -0.1, 34.75, is_urban=True),
    ("31", "Siaya", 0.05, 34.25),
    ("32", "Homa Bay", -0.5, 34.45),
    ("33", "Bar-el-Baringo", 1.35, 35.75),
    ("34", "Samburu", 1.85, 36.85),
    ("35", "Turkana", 3.05, 35.85),
    ("36", "West Pokot", 1.4, 34.8),
    ("37", "Nyeri", -0.55, 36.95),
    ("38", "Murang'a", -0.7, 37.2),
    ("39", "Kirinyaga", -0.4, 37.5),
    ("40", "Nakuru", -0.35, 36.2, is_urban=True),
    ("41", "Laikipia", -0.3, 36.55),
    ("42", "Nyandarua", -0.6, 36.35),
    ("43", "Eldoboret", 0.55, 35.3, is_urban=True),
    ("44", "Voi", -3.4, 38.6),
    ("45", "Bungoma", 0.6, 34.6),
    ("46", "Busia", 0.5, 33.9),
    ("47", "Kericho", -0.35, 35.3),
]


async def populate_synthetic_data():
    """Populate database with synthetic Kenya-wide data."""
    
    # Create engine
    engine = create_async_engine(
        settings.database_url,
        echo=False,
    )
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        # Create tables
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        print("✓ Tables created")
    
    async with async_session() as session:
        # Create admin user
        admin = User(
            username="admin",
            email="admin@floodguard.ke",
            hashed_password=hash_password("admin123"),
            role="admin",
            is_active=True,
        )
        session.add(admin)
        await session.flush()
        print("✓ Admin user created")
        
        # Create counties
        now = datetime.now(timezone.utc)
        
        for code, name, lat, lon, *args in COUNTIES_DATA:
            is_urban = args[0] if args else False
            
            # Create simple polygon around centroid (1km buffer)
            lon_delta = 0.01
            lat_delta = 0.01
            
            area = f"""MULTIPOLYGON(((
                {lon - lon_delta} {lat - lat_delta},
                {lon + lon_delta} {lat - lat_delta},
                {lon + lon_delta} {lat + lat_delta},
                {lon - lon_delta} {lat + lat_delta},
                {lon - lon_delta} {lat - lat_delta}
            )))"""
            
            centroid = f"POINT({lon} {lat})"
            
            county = County(
                code=code,
                name=name,
                geometry=area,
                centroid=centroid,
                is_urban=is_urban,
                population=random.randint(100_000, 2_000_000),
                area_km2=random.uniform(1000, 10_000),
                avg_elevation_m=random.randint(0, 4000),
                created_at=now,
            )
            
            session.add(county)
        
        await session.flush()
        print("✓ All 47 counties created")
        
        # Add synthetic barometer readings (last 7 days)
        from sqlalchemy import select
        counties_result = await session.execute(select(County))
        counties = counties_result.scalars().all()
        
        for i, county in enumerate(counties):
            for day in range(7):
                for hour in range(24):
                    if random.random() < 0.3:  # 30% sampling
                        timestamp = now - timedelta(days=day, hours=hour)
                        
                        reading = BarometerReading(
                            county_id=county.id,
                            device_id_hash=hash_device_id(f"device_{county.code}_{i}"),
                            location=f"POINT({random.uniform(33.9, 41.9)} {random.uniform(-4.7, 5.0)})",
                            pressure_hpa=random.uniform(980, 1020),
                            altitude_m=random.uniform(0, 3000),
                            temperature_c=random.uniform(15, 35),
                            humidity_pct=random.uniform(30, 90),
                            timestamp=timestamp,
                            created_at=timestamp,
                        )
                        
                        session.add(reading)
            
            if (i + 1) % 10 == 0:
                await session.flush()
                print(f"  Created readings for {i + 1} counties...")
        
        await session.commit()
        print(f"✓ Synthetic barometer readings created")
    
    await engine.dispose()
    print("✓ Database populated successfully")


if __name__ == "__main__":
    asyncio.run(populate_synthetic_data())

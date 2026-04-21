"""
County metadata loader.
Loads county geometries, centroids, and urban classification from database.

Design decisions:
- Cache county data in memory on startup (read-only throughout execution)
- Keyed by county_code ("01" to "47") for fast lookup
- Spatial index for point-in-polygon queries
- Distinguishes urban (GATv2) from rural (LSTM) counties
"""

from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class CountyLoader:
    """Loads and caches Kenya county metadata."""
    
    # Urban counties (use GATv2 infrastructure)
    URBAN_COUNTIES = {"01", "02", "04", "12", "30"}  # Nairobi, Mombasa, Kisumu, Nakuru, Eldoret codes (example)
    
    def __init__(self):
        """Initialize county loader."""
        self.counties: Dict[str, Dict] = {}
        self._loaded = False
    
    async def load_from_database(self, db_session):
        """
        Load county data from database.
        
        Called once during app startup to populate cache.
        
        Args:
            db_session: SQLAlchemy async session
        """
        from sqlalchemy import select
        from models.orm import County
        
        try:
            # Fetch all counties
            result = await db_session.execute(select(County))
            all_counties = result.scalars().all()
            
            for county in all_counties:
                self.counties[county.code] = {
                    "id": county.id,
                    "code": county.code,
                    "name": county.name,
                    "is_urban": county.is_urban,
                    "centroid": (county.centroid.x, county.centroid.y),
                    "population": county.population,
                    "area_km2": county.area_km2,
                    "avg_elevation_m": county.avg_elevation_m,
                }
            
            self._loaded = True
            logger.info(f"Loaded {len(self.counties)} counties from database")
        
        except Exception as e:
            logger.error(f"Failed to load counties: {e}")
            raise
    
    def is_loaded(self) -> bool:
        """Check if counties are loaded."""
        return self._loaded
    
    def get_county(self, county_code: str) -> Optional[Dict]:
        """Get county metadata by code."""
        return self.counties.get(county_code)
    
    def get_all_counties(self) -> Dict[str, Dict]:
        """Get all counties."""
        return self.counties
    
    def get_centroid(self, county_code: str) -> Optional[Tuple[float, float]]:
        """Get county centroid (lon, lat)."""
        county = self.get_county(county_code)
        return county["centroid"] if county else None
    
    def is_urban(self, county_code: str) -> bool:
        """Check if county is urban (uses GATv2)."""
        county = self.get_county(county_code)
        return county["is_urban"] if county else False
    
    def get_county_locations(self) -> Dict[str, Tuple[float, float]]:
        """Get all county centroids for batch weather fetching."""
        return {
            code: data["centroid"]
            for code, data in self.counties.items()
        }


# Global county loader instance
county_loader = CountyLoader()

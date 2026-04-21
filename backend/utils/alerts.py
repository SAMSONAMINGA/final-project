"""
Alert generation and dispatch via Africa's Talking SMS/USSD.
Generates natural-language messages in English, Swahili, and Sheng.

Design decisions:
- SMS ≤160 chars (one message)
- USSD ≤182 chars per frame
- Truncate SHAP factors to top-3 for brevity
- Hash phone numbers (SHA-256) before storing
- Include multilingual fallback (Swahili standard, Sheng slang)
"""

import hashlib
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timezone
import httpx

logger = logging.getLogger(__name__)


class AlertGenerator:
    """Generate alert messages based on flood risk."""
    
    # Risk level thresholds
    RISK_THRESHOLDS = {
        "Low": 0.25,
        "Medium": 0.50,
        "High": 0.75,
        "Critical": 1.0,
    }
    
    # Emoji/icons for different risk levels
    ICONS = {
        "Low": "✓",
        "Medium": "⚠",
        "High": "🔴",
        "Critical": "🚨",
    }
    
    # Message templates (English, Swahili, Sheng)
    TEMPLATES = {
        "en": {
            "Low": "FloodGuard: Low flood risk in {county}. Rainfall {rain:.1f}mm/h.",
            "Medium": "FloodGuard: MEDIUM flood risk in {county}. Rain {rain:.1f}mm/h. Avoid {factor}.",
            "High": "FloodGuard: HIGH flood risk in {county}! Risk {risk:.0%}. Move to high ground NOW.",
            "Critical": "🚨CRITICAL FLOOD WARNING {county}! Evacuation advised. Risk {risk:.0%}. Call 199.",
        },
        "sw": {
            "Low": "FloodGuard: Hatari ndogo ya mafuriko {county}. Mvua {rain:.1f}mm/h.",
            "Medium": "FloodGuard: Hatari KATIKATI {county}. Mvua {rain:.1f}mm/h. Epuka {factor}.",
            "High": "FloodGuard: Hatari KUBWA {county}! Jinga {risk:.0%}. Panda mlimani SASA.",
            "Critical": "🚨ONYO WA MAFURIKO {county}! Ambukizwa inasiwa. Jinga {risk:.0%}. Piga 199.",
        },
        "sh": {
            "Low": "BaajGuard: Khatari kadogo ya maji {county}. Mvua {rain:.1f}mm/h.",
            "Medium": "BaajGuard: Khatari KATI {county}. Mvua {rain:.1f}mm/h. Kaza {factor}.",
            "High": "BaajGuard: Khatari KUBWA {county}! Jinga {risk:.0%}. Kula mbegu YA.",
            "Critical": "🚨ONYO WA JINGA {county}! Inuka. Jinga {risk:.0%}. Piga 199.",
        },
    }
    
    # Feature name translations
    FEATURE_NAMES = {
        "en": {
            "drainage_capacity": "drainage blockage",
            "imperviousness": "concrete buildup",
            "elevation": "low elevation",
            "rainfall": "heavy rainfall",
            "soil_saturation": "wet soil",
        },
        "sw": {
            "drainage_capacity": "kuzuia",
            "imperviousness": "saruji nzito",
            "elevation": "kina chini",
            "rainfall": "mvua kali",
            "soil_saturation": "udongo manjano",
        },
        "sh": {
            "drainage_capacity": "kuzuia yote",
            "imperviousness": "baba ya saruji",
            "elevation": "kina kati",
            "rainfall": "mvua nzuri",
            "soil_saturation": "udongo mwete",
        },
    }
    
    def classify_risk(self, risk_score: float) -> str:
        """Classify risk score into level."""
        for level, threshold in sorted(self.RISK_THRESHOLDS.items(), key=lambda x: x[1]):
            if risk_score <= threshold:
                return level
        return "Critical"
    
    def get_top_factor(
        self,
        shap_factors: Optional[list],
        language: str = "en",
    ) -> str:
        """Get most important SHAP factor in target language."""
        if not shap_factors or len(shap_factors) == 0:
            return "heavy rain"
        
        top_factor = shap_factors[0]
        factor_name = top_factor.get("feature_name", "unknown")
        
        translations = self.FEATURE_NAMES.get(language, self.FEATURE_NAMES["en"])
        return translations.get(factor_name, factor_name)
    
    def generate_sms(
        self,
        county_name: str,
        county_code: str,
        risk_score: float,
        rainfall_mm_h: float,
        shap_factors: Optional[list] = None,
        language: str = "en",
    ) -> str:
        """
        Generate SMS alert message (≤160 chars).
        
        Args:
            county_name: Full county name
            county_code: 2-char code
            risk_score: 0-1 probability
            rainfall_mm_h: Current rainfall rate
            shap_factors: List of SHAP explanation dicts
            language: "en", "sw", or "sh"
        
        Returns:
            SMS text ≤160 chars
        """
        risk_level = self.classify_risk(risk_score)
        templates = self.TEMPLATES.get(language, self.TEMPLATES["en"])
        template = templates[risk_level]
        
        # Get top factor if available
        top_factor = self.get_top_factor(shap_factors, language)
        
        # Format message
        msg = template.format(
            county=county_code.upper(),
            rain=rainfall_mm_h,
            risk=risk_score,
            factor=top_factor,
        )
        
        # Truncate to 160 chars
        if len(msg) > 160:
            msg = msg[:157] + "..."
        
        return msg
    
    def generate_ussd(
        self,
        county_name: str,
        county_code: str,
        risk_score: float,
        rainfall_mm_h: float,
        shap_factors: Optional[list] = None,
        language: str = "en",
    ) -> str:
        """
        Generate USSD message (≤182 chars per frame).
        
        Args:
            county_name: Full county name
            county_code: 2-char code
            risk_score: 0-1 probability
            rainfall_mm_h: Current rain rate
            shap_factors: List of SHAP factors
            language: "en", "sw", or "sh"
        
        Returns:
            USSD text ≤182 chars
        """
        risk_level = self.classify_risk(risk_score)
        icon = self.ICONS[risk_level]
        
        top_factor = self.get_top_factor(shap_factors, language)
        
        # Minimal USSD format
        ussd_msg = (
            f"{icon} {county_code} {risk_level}\n"
            f"Risk: {risk_score:.0%} | Rain: {rainfall_mm_h:.0f}mm\n"
            f"Factor: {top_factor}"
        )
        
        # Truncate to 182 chars
        if len(ussd_msg) > 182:
            ussd_msg = ussd_msg[:179] + "..."
        
        return ussd_msg


class AfricasTalkingDispatcher:
    """Dispatch SMS/USSD via Africa's Talking API."""
    
    BASE_URL = "https://api.sandbox.africastalking.com"  # Change to production URL
    
    def __init__(self, api_key: str, username: str):
        """
        Initialize dispatcher.
        
        Args:
            api_key: Africa's Talking API key
            username: Africa's Talking username
        """
        self.api_key = api_key
        self.username = username
        self.client = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "apiKey": self.api_key,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
        return self.client
    
    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
    
    async def send_sms(
        self,
        phone_number: str,
        message: str,
    ) -> Optional[str]:
        """
        Send SMS via Africa's Talking.
        
        Args:
            phone_number: Destination phone number (with country code)
            message: SMS text (≤160 chars)
        
        Returns:
            Message ID if successful, None otherwise
        """
        try:
            client = await self._get_client()
            
            payload = {
                "username": self.username,
                "to": phone_number,
                "message": message,
            }
            
            response = await client.post(
                f"{self.BASE_URL}/version1/messaging",
                json=payload,
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract message ID from response
            if data.get("SMSMessageData", {}).get("Recipients"):
                msg_id = data["SMSMessageData"]["Recipients"][0]["messageId"]
                logger.info(f"SMS sent to {phone_number}: {msg_id}")
                return msg_id
            
            logger.warning(f"No message ID in response: {data}")
            return None
        
        except Exception as e:
            logger.error(f"Failed to send SMS to {phone_number}: {e}")
            return None
    
    async def send_ussd(
        self,
        phone_number: str,
        message: str,
    ) -> Optional[str]:
        """
        Send USSD via Africa's Talking.
        
        Args:
            phone_number: Destination phone number
            message: USSD text (≤182 chars)
        
        Returns:
            Message ID if successful, None otherwise
        """
        try:
            client = await self._get_client()
            
            payload = {
                "username": self.username,
                "to": phone_number,
                "message": message,
            }
            
            response = await client.post(
                f"{self.BASE_URL}/version1/ussd",
                json=payload,
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("USSDMessageData", {}).get("Recipients"):
                msg_id = data["USSDMessageData"]["Recipients"][0]["messageId"]
                logger.info(f"USSD sent to {phone_number}: {msg_id}")
                return msg_id
            
            logger.warning(f"No USSD message ID in response: {data}")
            return None
        
        except Exception as e:
            logger.error(f"Failed to send USSD to {phone_number}: {e}")
            return None


def hash_phone_number(phone_number: str) -> str:
    """Hash phone number for storage (SHA-256)."""
    return hashlib.sha256(phone_number.encode()).hexdigest()

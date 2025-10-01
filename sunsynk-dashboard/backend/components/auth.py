"""
Authentication Manager for Sunsynk Dashboard Phase 6
Handles JWT token validation and user authentication
"""

import jwt
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AuthManager:
    """Simple authentication manager for dashboard access"""
    
    def __init__(self, secret_key: str = "demo_key_change_in_production"):
        self.secret_key = secret_key
        self.algorithm = "HS256"
        
    def create_token(self, user_data: Dict[str, Any], expires_hours: int = 24) -> str:
        """Create a JWT token for user"""
        payload = {
            **user_data,
            "exp": datetime.utcnow() + timedelta(hours=expires_hours),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def create_demo_token(self) -> str:
        """Create a demo token for development"""
        demo_user = {
            "user_id": "demo_user",
            "username": "demo",
            "role": "admin"
        }
        return self.create_token(demo_user)
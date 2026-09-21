import os
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class SMSService(ABC):
    @abstractmethod
    def send_otp(self, phone_number: str, otp: str) -> bool:
        pass

class MockSMSService(SMSService):
    def send_otp(self, phone_number: str, otp: str) -> bool:
        print(f"\n[MOCK SMS] =========================================")
        print(f"[MOCK SMS] To: {phone_number}")
        print(f"[MOCK SMS] Message: Your PolicyPilot OTP is {otp}. Valid for 5 minutes.")
        print(f"[MOCK SMS] =========================================\n")
        logger.info(f"Mock SMS sent to {phone_number}")
        return True

class SMSServiceFactory:
    @staticmethod
    def get_service() -> SMSService:
        provider = os.getenv("SMS_PROVIDER", "mock").lower()
        if provider == "mock":
            return MockSMSService()
        else:
            # Here you would initialize AWS SNS, Twilio, Msg91, etc.
            # For now, fallback to mock if unknown provider
            logger.warning(f"Unknown SMS_PROVIDER '{provider}', falling back to mock")
            return MockSMSService()

# Global instance
sms_service = SMSServiceFactory.get_service()

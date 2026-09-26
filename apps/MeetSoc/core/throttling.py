from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginAnonThrottle(AnonRateThrottle):
    scope = "login_anon"


class OTPThrottle(AnonRateThrottle):
    scope = "otp"


class BurstUserThrottle(UserRateThrottle):
    scope = "burst"


class SustainedUserThrottle(UserRateThrottle):
    scope = "sustained"

"""Centralized configuration constants."""

# -- Ryanair API --
BASE_URL = "https://www.ryanair.com"
AVAILABLE_DATES_ENDPOINT = "/api/farfnd/v4/oneWayFares/{origin}/{destination}/availabilities"
FARFND_ONEWAY_FARES_ENDPOINT = "/api/farfnd/v4/oneWayFares"
ROUTES_ENDPOINT = "/api/views/locate/searchWidget/routes/en/airport/{iata}"
AIRPORTS_ENDPOINT = "/api/views/locate/5/airports/en/active"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT_SECONDS = 30
RATE_LIMIT_DELAY_SECONDS = 0.5

# -- Route defaults --
DEFAULT_ORIGIN = ""
DEFAULT_DESTINATION = ""
DEFAULT_CONNECTIONS: list[str] | None = None
DEFAULT_CURRENCY = "EUR"

# -- Connection constraints --
DEFAULT_MIN_CONNECTION_MINUTES = 60
DEFAULT_MAX_CONNECTION_HOURS = 8

# -- Cache --
DEFAULT_CACHE_EXPIRY_HOURS = 6
CONNECTIONS_FILENAME = "connections.json"

from supabase import create_client, Client
from ..config import get_settings

_settings = get_settings()
_supabase: Client | None = None

def get_client() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(_settings.supabase_url, _settings.supabase_service_role_key)
    return _supabase

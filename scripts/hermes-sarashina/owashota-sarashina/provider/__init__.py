"""Provider registration for the actual owashota runtime (no create_client hook required)."""
from providers import register_provider
from providers.base import ProviderProfile


class SarashinaProfile(ProviderProfile):
    def fetch_models(self, **kwargs):
        return ['sarashina3-mini']


register_provider(SarashinaProfile(
    name='sarashina', display_name='Sarashina3 mini (owashota)',
    api_mode='chat_completions', env_vars=('SARASHINA_API_KEY',),
    base_url='http://127.0.0.1:18761/v1',
    supports_health_check=False, supports_vision=False,
    supports_vision_tool_messages=False, supports_prompt_cache_key=False,
    fallback_models=('sarashina3-mini',), default_max_tokens=8000,
    default_aux_model='sarashina3-mini',
))

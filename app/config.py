"""환경설정 로더.

API 키는 서버(.env)에만 둔다. 프론트엔드/응답/깃에 절대 노출하지 않는다.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """.env에서 로드하는 앱 설정(키는 서버에만 보관)."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # 네이버 검색 API (1차 소스)
    naver_client_id: str = ""
    naver_client_secret: str = ""

    # 보조 소스 (2차, 선택)
    serper_api_key: str = ""
    google_cse_key: str = ""
    google_cse_cx: str = ""

    # 쿼터 / 캐시 가드
    search_cache_ttl: int = 86400
    naver_daily_quota_guard: int = 24000

    # 동작 옵션
    max_query_variants: int = 4
    naver_display: int = 20
    demo_mode: bool = False

    # CORS (프론트 dev 서버 + Capacitor/Electron 앱 오리진, 쉼표 구분)
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "capacitor://localhost,https://localhost,http://localhost"
    )

    @property
    def naver_configured(self) -> bool:
        """Naver configured."""
        return bool(self.naver_client_id and self.naver_client_secret)

    @property
    def serper_configured(self) -> bool:
        """Serper configured."""
        return bool(self.serper_api_key)

    @property
    def google_cse_configured(self) -> bool:
        """Google cse configured."""
        return bool(self.google_cse_key and self.google_cse_cx)

    @property
    def cors_origin_list(self) -> list[str]:
        """Cors origin list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """캐시된 Settings 싱글턴을 반환한다."""
    return Settings()

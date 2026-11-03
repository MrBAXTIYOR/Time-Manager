import pytest
from pydantic import ValidationError

from app.core.config import Settings
from tests.conftest import make_settings


def test_password_with_special_characters_is_escaped():
    s = make_settings(mysql_password="p@ss/w:rd#1")
    url = s.database_url
    assert url.password == "p@ss/w:rd#1"
    rendered = url.render_as_string(hide_password=False)
    assert "p@ss/w:rd#1" not in rendered  # it must be percent-encoded
    assert rendered.startswith("mysql+aiomysql://test_user:")


def test_secret_never_appears_in_repr_or_hidden_url():
    s = make_settings(mysql_password="super-secret")
    assert "super-secret" not in repr(s)
    assert "super-secret" not in str(s.database_url)  # SQLAlchemy masks as ***


def test_missing_required_secret_fails_fast(monkeypatch):
    for var in ("MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)  # type: ignore[call-arg]
    assert "mysql_password" in str(exc.value)


def test_invalid_environment_rejected():
    with pytest.raises(ValidationError):
        make_settings(app_env="staging-ish")


def test_is_production_flag():
    assert make_settings(app_env="production").is_production
    assert not make_settings().is_production

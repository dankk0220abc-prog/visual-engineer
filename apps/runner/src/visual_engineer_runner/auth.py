from pydantic import SecretStr


def bearer_header(token: SecretStr) -> dict[str, str]:
    return {"Authorization": f"Bearer {token.get_secret_value()}"}

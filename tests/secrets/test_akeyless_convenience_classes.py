from clearskies.secrets.akeyless import AkeylessAwsIam, AkeylessJwt, AkeylessSaml


def test_saml_defaults():
    secrets = AkeylessSaml(access_id="p-abc123")
    assert secrets.access_type == "saml"
    assert secrets.profile == "default"
    assert secrets.api_host == "https://api.akeyless.io"


def test_saml_custom_profile():
    assert AkeylessSaml(access_id="p-abc123", profile="work").profile == "work"


def test_jwt_defaults():
    secrets = AkeylessJwt(access_id="p-abc123", jwt_env_key="JWT")
    assert secrets.access_type == "jwt"
    assert secrets.jwt_env_key == "JWT"
    assert secrets.profile == "default"
    assert secrets.api_host == "https://api.akeyless.io"


def test_aws_iam_defaults():
    secrets = AkeylessAwsIam(access_id="p-abc123")
    assert secrets.access_type == "aws_iam"
    assert secrets.api_host == "https://api.akeyless.io"


def test_custom_api_host():
    assert AkeylessAwsIam(access_id="p-abc123", api_host="https://akeyless.example.com").api_host == (
        "https://akeyless.example.com"
    )

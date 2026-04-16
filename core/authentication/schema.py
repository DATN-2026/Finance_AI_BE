from drf_spectacular.extensions import OpenApiAuthenticationExtension


class JwtAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "core.authentication.permissions.JwtAuthentication"
    name = "BearerAuth"  # Match with SPECTACULAR_SETTINGS security scheme name

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }

"""Data validation schemas and serializers."""

from typing import Any, Dict, List, Optional, Type


class Field:
    """Base field class for schemas."""

    def __init__(self, required: bool = True, default: Any = None):
        self.required = required
        self.default = default

    def validate(self, value: Any) -> Any:
        if value is None:
            if self.required and self.default is None:
                raise ValueError("Field is required")
            return self.default
        return value


class StringField(Field):
    """String field validation."""

    def __init__(self, min_length: int = 0, max_length: int = 255, **kwargs):
        super().__init__(**kwargs)
        self.min_length = min_length
        self.max_length = max_length

    def validate(self, value: Any) -> str:
        value = super().validate(value)
        if not isinstance(value, str):
            raise ValueError("Must be a string")
        if len(value) < self.min_length:
            raise ValueError(f"Must be at least {self.min_length} characters")
        if len(value) > self.max_length:
            raise ValueError(f"Must be at most {self.max_length} characters")
        return value


class IntegerField(Field):
    """Integer field validation."""

    def __init__(
        self, min_value: Optional[int] = None, max_value: Optional[int] = None, **kwargs
    ):
        super().__init__(**kwargs)
        self.min_value = min_value
        self.max_value = max_value

    def validate(self, value: Any) -> int:
        value = super().validate(value)
        if not isinstance(value, int):
            raise ValueError("Must be an integer")
        if self.min_value is not None and value < self.min_value:
            raise ValueError(f"Must be at least {self.min_value}")
        if self.max_value is not None and value > self.max_value:
            raise ValueError(f"Must be at most {self.max_value}")
        return value


class Schema:
    """Base schema class."""

    def __init__(self, **fields):
        self.fields = fields

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data against schema."""
        result = {}
        errors = {}

        for name, field in self.fields.items():
            try:
                value = data.get(name)
                result[name] = field.validate(value)
            except ValueError as e:
                errors[name] = str(e)

        if errors:
            raise ValueError(f"Validation failed: {errors}")

        return result


# Common schemas
UserSchema = Schema(
    name=StringField(min_length=1, max_length=100),
    email=StringField(min_length=5, max_length=255),
    age=IntegerField(min_value=0, max_value=150, required=False),
)

ProjectSchema = Schema(
    name=StringField(min_length=1, max_length=100),
    description=StringField(required=False, default=""),
)

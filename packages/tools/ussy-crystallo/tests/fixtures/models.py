"""Sample models module for testing crystallo."""


class BaseModel:
    """Base model with common CRUD operations."""

    def __init__(self):
        self.id = None

    def save(self):
        pass

    def delete(self):
        pass

    def validate(self):
        pass


class UserModel(BaseModel):
    """User model."""

    def __init__(self):
        super().__init__()
        self.name = ""
        self.email = ""

    def save(self):
        pass

    def delete(self):
        pass

    def validate(self):
        pass

    def validate_email(self):
        pass

    def soft_delete(self):
        pass


class OrderModel(BaseModel):
    """Order model — broken symmetry: missing validate_email and soft_delete."""

    def __init__(self):
        super().__init__()
        self.total = 0.0
        self.status = ""

    def save(self):
        pass

    def delete(self):
        pass

    def validate(self):
        pass


class ProductModel(BaseModel):
    """Product model — has validate_email but shouldn't (accidental)."""

    def __init__(self):
        super().__init__()
        self.name = ""
        self.price = 0.0

    def save(self):
        pass

    def delete(self):
        pass

    def validate(self):
        pass

    def validate_email(self):
        pass


class GuestModel:
    """No base class but same structure — accidental symmetry."""

    def __init__(self):
        self.id = None
        self.name = ""
        self.email = ""

    def save(self):
        pass

    def delete(self):
        pass

    def validate(self):
        pass

    def validate_email(self):
        pass

    def soft_delete(self):
        pass

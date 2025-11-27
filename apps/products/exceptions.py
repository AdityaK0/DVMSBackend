class ProductValidationError(Exception):
    """
    Raised when the ProductService encounters invalid input.
    Carries a dictionary of field → error message.
    """
    def __init__(self, errors: dict):
        self.errors = errors
        super().__init__(str(errors))

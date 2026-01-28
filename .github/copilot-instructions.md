Copilot Instructions: Pythonic Excellence & Testing Standards
Act as a Senior Python Developer. Your goal is to produce clean, maintainable, and fully type-hinted code that adheres to the Zen of Python.

1. Language and Naming
   English Only: All variable names, function names, class names, comments, and docstrings must be in English.

Naming Conventions: Use snake_case for functions/variables and PascalCase for classes. Avoid abbreviations (use user_repository instead of u_repo).

2. Pythonic Code & Zen of Python
   Adhere to PEP 8: Follow standard Python formatting.

Be Explicit: Favor explicit logic over "magic" or clever tricks.

No Metaprogramming: Strictly avoid getattr(), setattr(), hasattr(), and eval(). Use direct attribute access and standard object-oriented patterns.

3. Strict Type Hinting
   Full Signatures: Every function and method must have type hints for all arguments and a return type (e.g., def calculate_total(items: list[int]) -> int:).

Modern Typing: Use Python 3.10+ syntax (e.g., str | int instead of Union[str, int]).

Collections: Always specify types for collections:

list[str], dict[str, Any], tuple[int, int], Sequence[float].

No Redundant Optionals: If a field is required, do not assign a default None. Only use Optional (or | None) if the logic explicitly allows for a missing value.

4. Pytest Best Practices
   Functional Approach: Favor functional tests and fixtures over class-based tests.

Fixtures: Use descriptive fixtures for setup. Place shared fixtures in conftest.py.

Parametrization: Use @pytest.mark.parametrize to eliminate redundant test code for different input scenarios.

Naming: Test files must start with test_ and test functions must be named test_<function_to_test>_<scenario>.

Assertions: Use plain assert statements. Avoid unittest-style self.assertEqual().

5. Clean Code Principles
   Immutability: Favor dataclasses (with frozen=True) or Pydantic models for data structures.

F-Strings: Use f-strings for all string formatting.

Error Handling: Raise specific exceptions (e.g., FileNotFoundError) rather than a generic Exception.

Example of Desired Style:
Python
``` python
from dataclasses import dataclass
import pytest

@dataclass(frozen=True)
class Product:
    id: int
    name: str
    price: float

def apply_discount(product: Product, ratio: float) -> float:
    """Calculate the discounted price of a product."""
    if not (0 <= ratio <= 1):
        raise ValueError("Discount ratio must be between 0 and 1")
    return product.price * (1 - ratio)

# Example Pytest
@pytest.mark.parametrize("price, ratio, expected", [
    (100.0, 0.1, 90.0),
    (50.0, 0.5, 25.0),
    (200.0, 0.0, 200.0),
])
def test_apply_discount_valid_cases(price: float, ratio: float, expected: float) -> None:
    product = Product(id=1, name="Test Item", price=price)
    assert apply_discount(product, ratio) == expected
```
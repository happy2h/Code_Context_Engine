"""
Test sample with complex call graph for Phase 2 testing
Contains:
- Multi-level call relationships
- Recursive calls
- Cross-file call references
"""


def helper_function(x):
    """A helper function called by multiple functions"""
    return x * 2


def recursive_factorial(n):
    """Recursive factorial function"""
    if n <= 1:
        return 1
    return n * recursive_factorial(n - 1)


def fibonacci(n):
    """Fibonacci function using helper"""
    if n <= 1:
        return n
    return helper_function(fibonacci(n - 1) + fibonacci(n - 2))


def process_data(data):
    """Main processing function with multi-level calls"""
    processed = []

    for item in data:
        # Call multiple functions
        item = helper_function(item)
        if item > 10:
            item = recursive_factorial(min(item, 5))
        processed.append(item)

    return processed


def main_entry():
    """Entry point that orchestrates all functions"""
    data = [1, 2, 3, 4, 5]
    result = process_data(data)
    result.append(fibonacci(10))
    return result

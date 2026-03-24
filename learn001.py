def binary_search(arr, target):
    """
    Perform binary search on a sorted list.

    Parameters:
        arr (list): A list of sorted elements
        target: The value to search for

    Returns:
        int: Index of target if found, otherwise -1
    """
    left = 0
    right = len(arr) - 1

    while left <= right:
        mid = (left + right) // 2

        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1


# Example usage
if __name__ == "__main__":
    numbers = [2, 4, 7, 10, 11, 32, 45, 87]
    target = 11

    index = binary_search(numbers, target)

    if index != -1:
        print(f"Element found at index {index}")
    else:
        print("Element not found")
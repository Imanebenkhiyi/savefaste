def parse_page_ranges(ranges_str, total_pages):
    """Parse a string like '1-3,5,7' into a list of page indices (0-based)."""
    result = set()
    parts = ranges_str.replace(' ', '').split(',')
    for part in parts:
        if '-' in part:
            start, end = map(int, part.split('-'))
            result.update(range(start - 1, min(end, total_pages)))
        else:
            num = int(part)
            if 1 <= num <= total_pages:
                result.add(num - 1)
    return sorted(result)

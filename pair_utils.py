import re


PAIR_COLUMN_PATTERN = re.compile(r"^ペア(\d+)_部品([123])$")
PART_POSITIONS = (1, 2, 3)


def get_pair_numbers(dataframe):
    """部品列が1つでも存在するペア番号を昇順で返す。"""
    numbers = set()
    for column in dataframe.columns:
        match = PAIR_COLUMN_PATTERN.match(str(column))
        if match:
            numbers.add(int(match.group(1)))
    return sorted(numbers)


def ensure_pair_columns(dataframe, pair_number, include_review=False):
    columns = [f"ペア{pair_number}_部品{position}" for position in PART_POSITIONS]
    if include_review:
        columns.extend([f"ペア{pair_number}_審議", f"ペア{pair_number}_審議理由"])

    for column in columns:
        if column not in dataframe.columns:
            dataframe[column] = ""
    return dataframe


def normalize_legacy_columns(dataframe):
    """旧「部品1/2(/3)」列をペア1へ移し、既存の新形式を優先する。"""
    legacy_columns = [column for column in ("部品1", "部品2", "部品3") if column in dataframe.columns]
    for position in PART_POSITIONS:
        legacy = f"部品{position}"
        current = f"ペア1_部品{position}"
        if legacy in dataframe.columns and current not in dataframe.columns:
            dataframe[current] = dataframe[legacy]
    if legacy_columns:
        dataframe = dataframe.drop(columns=legacy_columns)
    return dataframe


def normalize_part(value):
    if value is None:
        return ""
    try:
        if value != value:  # NaN / pd.NA
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def validate_parts(part1, part2, part3=""):
    """部品1・2を必須、部品3を任意として正規化する。"""
    parts = tuple(normalize_part(value) for value in (part1, part2, part3))
    if not parts[0] or not parts[1]:
        return None, "部品1と部品2を両方入力してください。部品3は任意です。"
    return parts, None


def pair_key(pair):
    if isinstance(pair, dict):
        return tuple(normalize_part(pair.get(f"part{position}", "")) for position in PART_POSITIONS)
    values = list(pair)
    values.extend([""] * (3 - len(values)))
    return tuple(normalize_part(value) for value in values[:3])


def format_parts(parts):
    return ", ".join(part for part in pair_key(parts) if part)

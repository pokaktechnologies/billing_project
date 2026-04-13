from datetime import datetime
import re

def generate_batch_number(model, field_name: str, prefix: str, length: int, course):
    year = datetime.now().year

    start = 1  # 001, 002...

    # Filter course-wise + year-wise
    latest = model.objects.filter(
        course=course,
        **{f"{field_name}__startswith": f"{prefix}{year}"}
    ).order_by(f"-{field_name}").first()

    if latest:
        latest_number_str = getattr(latest, field_name)[-length:]
        next_number = int(latest_number_str) + 1
    else:
        next_number = start

    return f"{prefix}{year}{next_number:0{length}d}"


from datetime import datetime

def generate_student_id(model, field_name: str, prefix: str, length: int):
    year = datetime.now().year

    latest = model.objects.select_for_update().filter(
        **{f"{field_name}__startswith": f"{prefix}{year}"}
    ).order_by(f"-{field_name}").first()

    if latest:
        latest_number_str = getattr(latest, field_name)[-length:]
        next_number = int(latest_number_str) + 1
    else:
        next_number = 1

    return f"{prefix}{year}{next_number:0{length}d}"

def get_clean_prefix(title):
    import re
    clean = re.sub(r'[^A-Za-z0-9 ]', '', title)
    words = clean.split()

    if len(words) > 1:
        return ''.join([w[0] for w in words]).upper()
    return clean[:3].upper()
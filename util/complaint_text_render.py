def process_complaint_text(text, complaint_keywords, keyword_field_map):
    original_text = text
    for kw in sorted(complaint_keywords, key=lambda x: x["startPosition"], reverse=True):
        start, length = kw["startPosition"], kw["length"]
        end = start + length
        domains = [keyword_field_map.get(str(d), "Unknown") for d in kw["domains"]]
        domains_str = ", ".join(domains)
        actual_word = original_text[start:end]
        replacement = (
            f'<strong '
            f'class="complaint-keyword" '
            f'data-bs-toggle="tooltip" '
            f'title="{domains_str}">'
            f'{actual_word}'
            f'</strong>'
        )
        text = text[:start] + replacement + text[end:]
    return text

def format_violation_scores(scores, keyword_field_map):
    return {
        keyword_field_map.get(str(k), k): {"score": round(v["score"], 3), "keywords": v["keywords"]}
        for k, v in scores.items()
    }
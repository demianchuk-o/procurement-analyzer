def process_complaint_text(text, complaint_keywords, keyword_field_map):
    for kw in sorted(complaint_keywords, key=lambda x: x["startPosition"], reverse=True):
        start = kw["startPosition"]
        length = kw["length"]
        end = start + length

        domains = [keyword_field_map.get(str(d), "Unknown") for d in kw["domains"]]
        domains_str = ", ".join(domains)
        replacement = (
            f'<b>{kw["keyword"]}</b>'
            f'<br><span style="color: blue;">({domains_str})</span><br>'
        )

        text = text[:start] + replacement + text[end:]
    return text
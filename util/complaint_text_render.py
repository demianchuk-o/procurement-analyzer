def process_complaint_text(text, complaint_keywords, keyword_field_map):
    processed_text = text
    offset = 0
    for keyword_data in complaint_keywords:
        keyword = keyword_data["keyword"]
        domains = keyword_data["domains"]
        start = keyword_data["startPosition"]
        length = keyword_data["length"]
        end = start + length

        domain_names = [keyword_field_map.get(str(domain), "Unknown") for domain in domains]
        domains_str = ", ".join(domain_names)

        replacement_text = (
            f'<b>{keyword}</b>'
            f'<br><span style="color: blue;">({domains_str})</span><br>'
        )

        new_start = start + offset
        new_end = end + offset
        processed_text = (
            processed_text[:new_start] + replacement_text + processed_text[new_end:]
        )
        offset += len(replacement_text) - length

    return processed_text
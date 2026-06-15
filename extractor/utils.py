def clean_text(text) :
    if not text :
        return None

    text = text.strip()
    text = " ".join(text.split())

    if text == "" :
        return None
    
    return text

def clean_list(items) :
    result = []

    for item in items :
        item = clean_text(item)

        if item and item not in result :
            result.append(item)

    return result
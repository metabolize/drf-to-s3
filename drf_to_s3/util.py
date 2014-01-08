def duplicates_in(list_value):
    '''Given a list, return a list of values which appear in it
    more than once.

    The order of items in the response is not guaranteed.

    '''
    from collections import Counter
    name_counter = Counter(list_value)
    return [k for k, count in name_counter.items() if count > 1]

def string_contains_only_url_characters(string_value):
    '''
    Return False if string_value contains non-URL characters.
    '''
    import string
    allowed_characters = "-._~:/?#[]@!$&'()*+,;=" + string.ascii_letters + string.digits
    return all([char in allowed_characters for char in string_value])

def string_is_valid_media_type(string_value):
    '''
    Return False if string_value is not a valid Media Type
    according to the RFC.
    '''
    import string
    allowed_characters = "!#$&.+-^_" + string.ascii_letters + string.digits
    try:
        first, rest = string_value.split('/', 1)
    except ValueError:
        return False
    allowed_characters = "!#$&.+-^_" + string.ascii_letters + string.digits
    return all([char in allowed_characters for char in first + rest])

def string_is_valid_filename(string_value):
    '''
    - Filenames shouldn't start with a space
    - Filenames should not contain null character
    - Filenames shouldn't contain unprintable characters
    - Filenames shouldn't contain non-ASCII characters
    '''
    import string
    allowed_characters = ' ' + string.printable
    return all([char in allowed_characters for char in string_value])

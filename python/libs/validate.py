def is_num(s):
    try:
        float(s)
    except ValueError:
        return False
    except TypeError:
        return False
    else:
        return True

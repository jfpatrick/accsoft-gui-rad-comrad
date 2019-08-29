# This file can be reused from Python snippets or specified as a main external file

def decorate(input: str) -> str:
    return f'<<{input}>>'

if __name__ == '__main__':
    output(decorate(new_val))
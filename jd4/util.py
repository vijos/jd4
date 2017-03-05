def read_text_file(file):
    with open(file) as f:
        return f.read()

def write_binary_file(file, data):
    with open(file, 'wb') as f:
        f.write(data)

def write_text_file(file, text):
    with open(file, 'w') as f:
        f.write(text)

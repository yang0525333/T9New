import magic

file_path = 'T9.db'
mime = magic.Magic(mime=True)
file_type = mime.from_file(file_path)
print(f'MIME type: {file_type}')

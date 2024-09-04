import os

# List of directories to exclude
EXCLUDED_DIRS = {
    'node_modules', 'venv', '.venv', 'env', '.env', '.git', '__pycache__',
    'build', 'dist', '.idea', '.vscode'
}

# List of file extensions to exclude
EXCLUDED_EXTENSIONS = {
    # Binary files
    '.pyc', '.pyo', '.pyd', '.obj', '.exe', '.dll', '.so', '.dylib',
    # Image files
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico',
    # Audio/Video files
    '.mp3', '.mp4', '.avi', '.mov',
    # Archive files
    '.zip', '.tar', '.gz', '.rar',
    # Database files
    '.db', '.sqlite', '.sqlite3',
    # Other non-text files
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    # Large data files
    '.csv', '.json', '.xml'
}


def read_file(path: str) -> str:
    try:
        with open(path, mode="r", encoding="utf-8") as reader:
            return reader.read()
    except Exception as e:
        return f"Error reading {path}: {str(e)}"


def get_every_file_content_in_folder(folder_path: str) -> str:
    all_contents = ""
    for root, dirs, files in os.walk(folder_path):
        # Remove excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        file_end_delimiter = "\n\n*" * 50 + "EOF" + "*" * 50 + "\n\n*"
        for file in files:
            file_extension = os.path.splitext(file)[1].lower()
            if file_extension not in EXCLUDED_EXTENSIONS:
                file_path = os.path.join(root, file)
                file_content = read_file(file_path)
                all_contents += f"Location: {file_path}\n{file_content}\n\n"
                all_contents += file_end_delimiter
    print("Reading done")
    return all_contents
# def write_file() -> None:
#     content = get_every_file_content_in_folder(folder_path="./app")
#     with open("output.txt", mode="w", encoding="utf-8") as writer:
#         writer.write(content)


# write_file()

import os

from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

from app.core.jina_ai import use_jina

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
    '.csv', '.json', '.xml',
    # Configuration files
    '.gitignore'
}

INCLUDED_LANGUAGE_WITH_EXTENSION = {
    "cpp",
    "go",
    "java",
    "kotlin",
    "js",
    "ts",
    "php",
    "proto",
    "python",
    "rst",
    "ruby",
    "rust",
    "scala",
    "swift",
    "markdown",
    "latex",
    "html",
    "sol",
    "csharp",
    "cobol",
    "c",
    "lua",
    "perl",
    "haskell"
}

OTHER_ALLOWED_CONFIG_EXT = {
    "yaml", "yml", "json", "toml", "ini",
    "cfg", "conf", "properties", "env"
}


def read_file(path: str) -> str:
    try:
        with open(path, mode="r", encoding="utf-8") as reader:
            return reader.read()
    except Exception as e:
        return f"Error reading {path}: {str(e)}"


def get_every_file_content_in_folder(folder_path: str, is_code: bool) -> str:
    all_contents = ""
    chunks = []
    for root, dirs, files in os.walk(folder_path):
        # Remove excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        file_end_delimiter = "\n\n" + "*" * 50 + "EOF" + "*" * 50 + "\n\n"
        for file in files:
            file_extension = os.path.splitext(file)[1].lower()
            if file_extension not in EXCLUDED_EXTENSIONS:
                file_path = os.path.join(root, file)
                file_content = read_file(file_path)
                file_content += f"Location: {file_path}\n{file_content}\n\n"
                file_content += file_end_delimiter
                all_contents += file_content
                if is_code:
                    ext = file_extension[1:]
                    if ext in INCLUDED_LANGUAGE_WITH_EXTENSION:
                        chunks.append(chunk_code(file_content, ext, 1000))
                    elif ext in OTHER_ALLOWED_CONFIG_EXT:
                        chunks.append(chunk_text(file_content, 1000))
    print("Reading done")
    # print(chunks)
    # [write_file(" ".join(chunk)) for chunk in chunks]
    return {
        "content": all_contents,
        "chunks": chunks,
        "size": len(chunks)
    }

def write_file(data: str) -> None:
    # content = get_every_file_content_in_folder(folder_path="./app")
    with open("output.txt", mode="+a", encoding="utf-8") as writer:
        writer.write(data)

def chunk_code(content: str, ext: str, context_size: int):
    if ext == 'rs':
        ext = 'rust'
    if ext == 'c++':
        ext = 'cpp'
    if ext == 'cs':
        ext = 'csharp'
    splitter = RecursiveCharacterTextSplitter.from_language(
        language=ext,
        chunk_size=context_size,
        chunk_overlap=0
    )
    splits = splitter.create_documents([content])
    split_sts = [split.page_content for split in splits]
    return split_sts

def chunk_text(content: str, context_size: int):
    chunks = use_jina.segment_data(content)
    if "chunks" in chunks.keys():
        return chunks["chunks"]
    return []
import os

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.jina_ai import use_jina
from app.schemas import Metadata
from app.schemas.Common import AgentResponse
from app.schemas.Metadata import GitSpecificMd, Metadata

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
    """
    Read the contents of a file.

    Args:
        path (str): The path to the file to be read.

    Returns:
        str: The contents of the file, or an error message if reading fails.
    """
    try:
        with open(path, mode="r", encoding="utf-8") as reader:
            return reader.read()
    except Exception as e:
        return f"Error reading {path}: {str(e)}"


def get_every_file_content_in_folder(folder_path: str, is_code: bool, repo_link: str, md: Metadata[GitSpecificMd], mem_id) -> AgentResponse:
    """
    Get the content of every file in a folder and its subfolders, with chunks and metadata.

    Args:
        folder_path (str): The path to the folder to read.
        is_code (bool): Whether to include code files only.
        repo_link (str): The link to the repository.

    Returns:
        AgentResponse: A dictionary containing:
            - 'content': The concatenated content of all files.
            - 'chunks': List of content chunks.
            - 'metadata': List of metadata for each chunk.
    """
    if not os.path.exists(folder_path):
        raise ValueError(f"Folder '{folder_path}' does not exist.")

    all_contents = ""
    chunks = []
    repo_name = repo_link.split("/")[-1]
    repo_creator_name = repo_link.split("/")[3]
    chunk_id = 0
    metadata = []
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
                current_md = md.copy()
                if is_code:
                    ext = file_extension[1:]
                    if ext in INCLUDED_LANGUAGE_WITH_EXTENSION:
                        code_chunks = chunk_code(file_content, ext, 1000)
                        chunks.extend(code_chunks)
                        for i in range(len(code_chunks)):
                            current_md.specific_desc = GitSpecificMd(
                                repo_name=repo_name,
                                repo_creator_name=repo_creator_name,
                                file_name=file_path,
                                programming_language=ext,
                                chunk_type="code",
                                chunk_id=f"{mem_id}_{chunk_id}"
                            )
                            metadata.append(current_md)
                            chunk_id += 1
                    elif ext in OTHER_ALLOWED_CONFIG_EXT:
                        code_chunks = chunk_text(file_content, 500)
                        chunks.extend(code_chunks)
                        for i in range(len(code_chunks)):
                            current_md.specific_desc = GitSpecificMd(
                                repo_name=repo_name,
                                repo_creator_name=repo_creator_name,
                                file_name=file_path,
                                programming_language=ext,
                                chunk_type="code",
                                chunk_id=f"{chunk_id}"
                            )
                            metadata.append(current_md)
                            chunk_id += 1

                    # chunk_id += 1
    print(len(all_contents))
    print(len(chunks))
    print(len(metadata))
    print("done here")
    return AgentResponse(
        transcript=all_contents,
        chunks=chunks,
        metadata=metadata,
        userId=md.user_id,
        memoryId=md.memId
    )


def write_file(data: str) -> None:
    """
    Write data to a file named 'output.txt'.

    Args:
        data (str): The data to be written to the file.
    """
    with open("output.txt", mode="+a", encoding="utf-8") as writer:
        writer.write(data)


def chunk_code(content: str, ext: str, context_size: int) -> list:
    """
    Split code content into chunks using a language-specific splitter.

    Args:

        content (str): The code content to be split.
        ext (str): The file extension indicating the programming language.
        context_size (int): The desired size of each chunk.

    Returns:
        list: A list of code chunks.
    """
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
    return [split.page_content for split in splits]


def chunk_text(content: str, context_size: int) -> list:
    """
    Split text content into chunks using Jina AI.

    Args:
        content (str): The text content to be split.
        context_size (int): The desired size of each chunk (not used in this implementation).

    Returns:
        list: A list of text chunks, or an empty list if chunking fails.
    """
    chunks = use_jina.segment_data(content)
    return chunks

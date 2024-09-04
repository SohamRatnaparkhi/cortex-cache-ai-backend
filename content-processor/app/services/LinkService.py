from app.core.agents import LinkAgents


def get_code_from_git_repo(repo_url: str) -> dict:
    git_agent = LinkAgents.GitAgent(repo_url)
    return git_agent.process_media()


# def clone_git_repo(repo_url: str) -> Union[bool, str]:
#     try:
#         repo_name = repo_url.split('/')[-1]
#         path = f'./tmp/git_repo/{repo_name}'
#         # create a folder at the path if it doesn't exist
#         os.makedirs(path, exist_ok=True)
#         Repo.clone_from(repo_url, path)
#         return True, path
#     except Exception as e:
#         return False, f"Error cloning {repo_url}: {str(e)}"
#     finally:
#         return False, None
    
# def extract_code_from_repo(repo_url: str) -> Union[bool, str]:
#     success, path = clone_git_repo(repo_url)
#     if not success:
#         return success, path
    
#     content = get_every_file_content_in_folder(path)
#     return True, content

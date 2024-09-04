from abc import ABC, abstractmethod

from app.utils.Link import clone_git_repo, extract_code_from_repo


class LinkAgent(ABC):
    def __init__(self, resource_link) -> None:
        super().__init__()
        self.resource_link = resource_link

    @abstractmethod
    async def process_media(self) -> dict:
        pass


class GitAgent(LinkAgent):
    def process_media(self):
        repo_url = self.resource_link
        code = extract_code_from_repo(repo_url=repo_url)
        return {"code": code}

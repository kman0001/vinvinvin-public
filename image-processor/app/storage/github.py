import base64
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.storage.base import Storage


class GitHubStorage(Storage):

    def __init__(
        self,
        config
    ):
        super().__init__(
            config
        )

        self.token = self._resolve_token(
            config["token"]
        )

        self.repository = config["repository"]

        self.branch = config.get(
            "branch",
            "main"
        )

        self.base_path = config.get(
            "path",
            ""
        ).strip(
            "/"
        )

        self.output_mode = config.get(
            "output_mode",
            "filename"
        )

        self.base_url = config.get(
            "base_url",
            ""
        ).rstrip(
            "/"
        )

        self.pending_changes = {}

        if "/" not in self.repository:
            raise ValueError(
                "github.repository must be in owner/repository form"
            )

        if (
            self.output_mode == "url"
            and not self.base_url
        ):
            raise ValueError(
                "github.base_url is required when output_mode=url"
            )

        if not self.token:
            raise ValueError(
                "github.token is required"
            )

    def _resolve_token(
        self,
        value
    ):
        value = str(
            value
        ).strip()

        if (
            value.startswith("${")
            and value.endswith("}")
        ):
            return os.environ.get(
                value[2:-1],
                ""
            )

        if value.startswith("env:"):
            return os.environ.get(
                value[4:],
                ""
            )

        return value

    def _repo_url(
        self,
        path
    ):
        return (
            "https://api.github.com/repos/"
            f"{self.repository}/{path.lstrip('/')}"
        )

    def _git_path(
        self,
        destination
    ):
        return "/".join(
            part
            for part in (
                self.base_path,
                destination.strip(
                    "/"
                )
            )
            if part
        )

    def _url(
        self,
        destination
    ):
        encoded = "/".join(
            quote(
                part,
                safe=""
            )
            for part in self._git_path(
                destination
            ).split(
                "/"
            )
        )

        return self._repo_url(
            f"contents/{encoded}"
        )

    def _request(
        self,
        method,
        url,
        body=None
    ):
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": (
                f"Bearer {self.token}"
            ),
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": (
                "vinvinvin-image-processor/1.0"
            ),
        }

        data = None

        if body is not None:
            data = json.dumps(
                body
            ).encode(
                "utf-8"
            )

            headers[
                "Content-Type"
            ] = "application/json"

        request = Request(
            url,
            data=data,
            headers=headers,
            method=method
        )

        return urlopen(
            request,
            timeout=30
        )

    def _get_sha(
        self,
        destination
    ):
        try:
            url = (
                f"{self._url(destination)}"
                f"?ref={self.branch}"
            )

            with self._request(
                "GET",
                url
            ) as response:
                return json.load(
                    response
                ).get(
                    "sha"
                )

        except HTTPError as exc:
            if exc.code == 404:
                return None

            raise

    def _get_public_url(
        self,
        destination
    ):
        if self.output_mode != "url":
            return None

        return (
            f"{self.base_url}/"
            f"{destination.lstrip('/')}"
        )

    def upload(
        self,
        source: Path,
        destination: str
    ):
        self.pending_changes[
            destination
        ] = source.read_bytes()

        return {
            "path": destination,
            "url": self._get_public_url(
                destination
            )
        }

    def delete(
        self,
        destination: str
    ):
        self.pending_changes[
            destination
        ] = None

    def exists(
        self,
        destination: str
    ):
        if destination in self.pending_changes:
            return (
                self.pending_changes[
                    destination
                ] is not None
            )

        return (
            self._get_sha(
                destination
            )
            is not None
        )

    def get_file_content(
        self,
        destination: str
    ):
        if destination in self.pending_changes:
            content = self.pending_changes[
                destination
            ]

            if content is None:
                raise FileNotFoundError(
                    destination
                )

            return content

        url = (
            f"{self._url(destination)}"
            f"?ref={self.branch}"
        )

        with self._request(
            "GET",
            url
        ) as response:
            data = json.load(
                response
            )

        return base64.b64decode(
            data["content"]
        )

    def download(
        self,
        source,
        destination
    ):
        content = self.get_file_content(
            source
        )

        with Path(
            destination
        ).open(
            "wb"
        ) as output:
            output.write(
                content
            )

    def _get_branch_ref(self):
        with self._request(
            "GET",
            self._repo_url(
                f"git/ref/heads/{self.branch}"
            )
        ) as response:
            return json.load(
                response
            )

    def _get_commit(
        self,
        sha
    ):
        with self._request(
            "GET",
            self._repo_url(
                f"git/commits/{sha}"
            )
        ) as response:
            return json.load(
                response
            )

    def _create_blob(
        self,
        content
    ):
        payload = {
            "content": base64.b64encode(
                content
            ).decode(
                "ascii"
            ),
            "encoding": "base64"
        }

        with self._request(
            "POST",
            self._repo_url(
                "git/blobs"
            ),
            payload
        ) as response:
            return json.load(
                response
            )["sha"]

    def _create_tree(
        self,
        base_tree_sha,
        tree
    ):
        payload = {
            "base_tree": base_tree_sha,
            "tree": tree
        }

        with self._request(
            "POST",
            self._repo_url(
                "git/trees"
            ),
            payload
        ) as response:
            return json.load(
                response
            )["sha"]

    def _create_commit(
        self,
        parent_sha,
        tree_sha
    ):
        payload = {
            "message": "Update menu images",
            "tree": tree_sha,
            "parents": [
                parent_sha
            ]
        }

        with self._request(
            "POST",
            self._repo_url(
                "git/commits"
            ),
            payload
        ) as response:
            return json.load(
                response
            )["sha"]

    def _update_ref(
        self,
        commit_sha
    ):
        payload = {
            "sha": commit_sha,
            "force": False
        }

        with self._request(
            "PATCH",
            self._repo_url(
                f"git/refs/heads/{self.branch}"
            ),
            payload
        ):
            pass

    def flush(self):
        if not self.pending_changes:
            return

        ref = self._get_branch_ref()

        parent_sha = ref[
            "object"
        ]["sha"]

        parent_commit = self._get_commit(
            parent_sha
        )

        base_tree_sha = parent_commit[
            "tree"
        ]["sha"]

        tree = []

        for (
            destination,
            content
        ) in self.pending_changes.items():

            entry = {
                "path": self._git_path(
                    destination
                ),
                "mode": "100644",
                "type": "blob"
            }

            if content is None:
                entry["sha"] = None

            else:
                entry["sha"] = self._create_blob(
                    content
                )

            tree.append(
                entry
            )

        tree_sha = self._create_tree(
            base_tree_sha,
            tree
        )

        commit_sha = self._create_commit(
            parent_sha,
            tree_sha
        )

        self._update_ref(
            commit_sha
        )

        print(
            "[INFO] GitHub batch commit created: "
            f"{len(self.pending_changes)} file changes",
            flush=True
        )

        self.pending_changes.clear()
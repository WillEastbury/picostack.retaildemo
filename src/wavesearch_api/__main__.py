from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run("wavesearch_api.app:create_app", factory=True, host="127.0.0.1", port=8803)


if __name__ == "__main__":
    main()

from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run("wavesearch_frontend.app:create_app", factory=True, host="127.0.0.1", port=8806)


if __name__ == "__main__":
    main()

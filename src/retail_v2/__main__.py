from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run("retail_v2.app:create_app", factory=True, host="127.0.0.1", port=8797)


if __name__ == "__main__":
    main()

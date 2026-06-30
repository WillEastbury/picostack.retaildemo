from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run("wavestore_erp_frontend.app:create_app", factory=True, host="127.0.0.1", port=8805)


if __name__ == "__main__":
    main()

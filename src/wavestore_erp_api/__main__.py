from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run("wavestore_erp_api.app:create_app", factory=True, host="127.0.0.1", port=8802)


if __name__ == "__main__":
    main()

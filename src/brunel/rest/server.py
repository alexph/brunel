from brunel.rest.app import app


def server():
    import uvicorn

    reload = True

    uvicorn.run(
        "brunel.rest.app:app" if reload else app,
        host="0.0.0.0",
        port=8011,
        reload=reload,
    )

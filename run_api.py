import uvicorn

if __name__ == "__main__":
    print("Starting ChefByte API server...")
    # Use reload=True for development, which automatically restarts the server
    # when code changes are detected. Remove or set to False for production.
    # host='0.0.0.0' makes the server accessible on your network.
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True) 
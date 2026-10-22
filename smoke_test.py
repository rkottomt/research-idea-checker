import chromadb

client = chromadb.PersistentClient(path="./chroma_store")  # writes to disk, survives restarts
collection = client.get_or_create_collection(name="smoke_test")
print("chromadb", chromadb.__version__, "| collections:", [c.name for c in client.list_collections()])
print("items in smoke_test:", collection.count())

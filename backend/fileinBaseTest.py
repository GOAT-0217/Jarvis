from rag_utils import retrieve_documents
result = retrieve_documents("离婚冷静期", top_k=3)
print(len(result["docs"]))
for doc in result["docs"]:
    print(doc.get("filename"), doc.get("text", "")[:100])
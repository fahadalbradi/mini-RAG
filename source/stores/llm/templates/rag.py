from string import Template

system_prompt = "\n".join([
    "You are an assistant that answers questions using ONLY the documents provided by the user.",
    "Documents are numbered; cite the ones you use like [1], [2].",
    "If the documents do not contain the answer, say you could not find it in the uploaded files.",
    "Answer in the same language as the question. Be precise and concise.",
])

document_prompt = Template("\n".join([
    "## Document [$doc_num]",
    "$chunk_text",
]))

footer_prompt = Template("\n".join([
    "Based only on the documents above, answer the question.",
    "## Question:",
    "$query",
    "",
    "## Answer:",
]))

from typing import List, Callable, Any, Optional, Type
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, Runnable
from langchain_core.output_parsers import StrOutputParser
from langchain.agents import tool
from langchain.tools import BaseTool
from langchain.pydantic_v1 import BaseModel, Field
from langchain.callbacks.manager import CallbackManagerForToolRun
from functools import wraps

__DEFAULT_QA_CHAIN_PROMPT = """
你要严格依据如下资料回答问题，你的回答不能与其冲突，更不要编造。
请始终使用中文回答。

{context}

问题: {question}
"""

def create_qa_chain(llm: Runnable, retriever: Callable, prompt: str = __DEFAULT_QA_CHAIN_PROMPT) -> Callable:
    prompt = ChatPromptTemplate.from_template(prompt)

    def format_docs(docs: List[str]) -> str:
        return "\n\n".join([d.page_content for d in docs])

    return (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

def make_safe_tool(func: Callable) -> Callable:
    """Create a new function that wraps the given function with error handling"""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        try:
            return str(func(*args, **kwargs))
        except Exception as e:
            return str(e)
    return wrapper

class SearchInput(BaseModel):
    query: str = Field(title = "提问内容", description="用户问题的文字描述，必须是字符串")

class AskDocumentTool(BaseTool):
    name = "ask_document"
    description = """根据资料库回答问题。考虑上下文信息，确保问题对相关概念的定义表述完整。
    args:
    - query 类型是str, 用户问题的文字描述
    """
    args_schema: Type[BaseModel] = SearchInput
    qa_chain: Runnable = Field(...)

    def _run(
        self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool."""
        return self.qa_chain.invoke(query)

def create_qa_toolkits(qa_chain: Runnable) -> List[AskDocumentTool]:
    return [AskDocumentTool(qa_chain=qa_chain)]
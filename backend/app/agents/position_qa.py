from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enums import PositionCode
from app.models.knowledge import KnowledgeChunk
from app.repositories.knowledge import retrieve_published_chunks, source_for_chunk
from app.schemas.chat import ChatResponse, Citation

REFUSAL = "当前已审核工作细则未包含此要求，请联系管理员确认。"


class DraftAnswer(BaseModel):
    answer: str
    citation_ids: list[int] = Field(default_factory=list)


class QAState(TypedDict, total=False):
    question: str
    position_code: PositionCode
    chunks: list[KnowledgeChunk]
    answer: str
    citations: list[Citation]
    refusal: bool


def build_position_qa_graph(db: Session):
    settings = get_settings()

    def retrieve(state: QAState):
        chunks = retrieve_published_chunks(db, state["position_code"], state["question"])
        return {"chunks": chunks}

    def answer(state: QAState):
        chunks = state.get("chunks", [])
        if not chunks or not settings.llm_api_key or not settings.llm_model:
            return {"answer": REFUSAL, "citations": [], "refusal": True}
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model=settings.llm_model, api_key=settings.llm_api_key, base_url=settings.llm_base_url or None, temperature=0)
        structured = llm.with_structured_output(DraftAnswer)
        context = "\n\n".join(f"[chunk_id={chunk.id}] {chunk.content}" for chunk in chunks)
        draft = structured.invoke([
            ("system", "仅依据提供的幼儿园已审核工作细则回答。不得使用常识补充，不得推断缺失要求。回答中每个依据都必须引用给出的 chunk_id。若依据不足，回答固定文本：" + REFUSAL),
            ("human", f"问题：{state['question']}\n已审核细则：\n{context}"),
        ])
        allowed = {chunk.id for chunk in chunks}
        cited = set(draft.citation_ids)
        if not draft.answer.strip() or not cited or not cited.issubset(allowed) or draft.answer.strip() == REFUSAL:
            return {"answer": REFUSAL, "citations": [], "refusal": True}
        citations = [Citation(**source_for_chunk(db, chunk)) for chunk in chunks if chunk.id in cited]
        return {"answer": draft.answer.strip(), "citations": citations, "refusal": False}

    graph = StateGraph(QAState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("answer", answer)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "answer")
    graph.add_edge("answer", END)
    return graph.compile()


def ask_position_question(db: Session, position_code: PositionCode, question: str) -> ChatResponse:
    result = build_position_qa_graph(db).invoke({"question": question, "position_code": position_code})
    return ChatResponse(answer=result["answer"], citations=result.get("citations", []), refusal=result["refusal"])

"""Live pipeline population — replace static contexts/answers with real pipeline output.

Single responsibility: given a gold dataset, query the production ``HybridRetriever`` for
contexts and run the production compliance agent for answers, keeping ``question`` and
``ground_truth`` from the evalset. Backend imports are deferred so static-only runs never
pay the cost of loading the agent/retriever stack.
"""
from __future__ import annotations

from uuid import uuid4

from cora_rc_ai.evaluation.config import EvalConfig


class AgentRunner:
    """Thin adapter around an ADK ``Runner`` that returns a single final answer string."""

    def __init__(self, runner, session_service, app_name: str):
        self._runner = runner
        self._session_service = session_service
        self._app_name = app_name

    async def run(self, question: str) -> str:
        from google.genai.types import Content, Part  # noqa: PLC0415

        user_id = "eval_user"
        session_id = str(uuid4())
        await self._session_service.create_session(
            app_name=self._app_name, user_id=user_id, session_id=session_id
        )
        user_message = Content(role="user", parts=[Part.from_text(text=question)])

        full_response = ""
        async for event in self._runner.run_async(
            user_id=user_id, session_id=session_id, new_message=user_message
        ):
            if event.is_final_response() and event.content and event.content.parts:
                full_response = "".join(p.text for p in event.content.parts if p.text)
        return full_response


class LivePipelinePopulator:
    """Populate ``contexts``/``answer`` from the real retriever + compliance agent."""

    def __init__(self, config: EvalConfig):
        self._config = config

    def _build(self):
        """Lazily construct retriever + agent runner (heavy backend imports)."""
        from cora_rc_ai.backend_agentic.tools.rag_tool import get_retriever  # noqa: PLC0415
        from cora_rc_ai.backend_agentic.agents.compliance_agent import (  # noqa: PLC0415
            compliance_agent,
        )
        from google.adk.runners import Runner  # noqa: PLC0415
        from google.adk.sessions.in_memory_session_service import (  # noqa: PLC0415
            InMemorySessionService,
        )

        retriever = get_retriever()
        session_service = InMemorySessionService()
        runner = Runner(
            app_name=self._config.app_name,
            agent=compliance_agent,
            session_service=session_service,
        )
        agent_runner = AgentRunner(runner, session_service, self._config.app_name)
        return retriever, agent_runner

    def _retrieve_contexts(self, retriever, question: str, index: int) -> list[str]:
        try:
            chunks = retriever.retrieve(question, limit=self._config.live_retrieve_limit)
            contexts = [c.get("chunk_text", "") for c in chunks if c.get("chunk_text")]
        except Exception as exc:  # noqa: BLE001
            print(f"[{index}] retrieval failed: {exc}")
            contexts = []
        return contexts or [""]  # ragas needs a non-empty list

    async def _generate_answer(self, agent_runner: AgentRunner, question: str, index: int) -> str:
        try:
            return await agent_runner.run(question)
        except Exception as exc:  # noqa: BLE001
            print(f"[{index}] agent failed: {exc}")
            return ""

    async def populate(self, test_data: dict) -> dict:
        retriever, agent_runner = self._build()

        questions = test_data["question"]
        live_contexts: list[list[str]] = []
        live_answers: list[str] = []

        for i, question in enumerate(questions):
            live_contexts.append(self._retrieve_contexts(retriever, question, i))
            live_answers.append(await self._generate_answer(agent_runner, question, i))
            print(f"[{i + 1}/{len(questions)}] live pipeline done for: {question[:60]}...")

        data = dict(test_data)
        data["contexts"] = live_contexts
        data["answer"] = live_answers
        return data

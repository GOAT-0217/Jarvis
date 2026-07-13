from dotenv import load_dotenv
import os
import json
import asyncio
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk, SystemMessage
from tools import get_current_weather, search_knowledge_base, get_last_rag_context, reset_tool_call_guards, set_rag_step_queue
from datetime import datetime
from cache import cache
from database import SessionLocal
from models import User, ChatSession, ChatMessage

load_dotenv()

API_KEY = os.getenv("ARK_API_KEY")
MODEL = os.getenv("MODEL")
BASE_URL = os.getenv("BASE_URL")

class ConversationStorage:
    """对话存储（PostgreSQL + Redis）。"""

    @staticmethod
    def _messages_cache_key(user_id: str, session_id: str) -> str:
        # 结合用户和会话ID生成消息缓存键
        return f"chat_messages:{user_id}:{session_id}"

    @staticmethod
    def _sessions_cache_key(user_id: str) -> str:
        # 仅根据用户ID生成会话列表缓存键，便于在缓存系统中隔离和检索不同维度的聊天数据。
        return f"chat_sessions:{user_id}"

    @staticmethod
    def _to_langchain_messages(records: list[dict]) -> list:
        # 该函数将字典列表转换为LangChain消息对象
        messages = []
        for msg_data in records:
            msg_type = msg_data.get("type")
            content = msg_data.get("content", "")
            if msg_type == "human":
                messages.append(HumanMessage(content=content))
            elif msg_type == "ai":
                messages.append(AIMessage(content=content))
            elif msg_type == "system":
                messages.append(SystemMessage(content=content))
        return messages

    def save(self, user_id: str, session_id: str, messages: list, metadata: dict = None, extra_message_data: list = None):
        """保存对话"""
        """
        该函数用于持久化对话数据：
            1.校验用户并获取或创建会话；
            2.清空旧消息，批量插入新消息及RAG追踪信息；
            3.更新会话时间并提交事务；
            4.同步更新缓存，确保数据库与缓存一致性。
        """
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == user_id).first()
            if not user:
                return

            session = (
                db.query(ChatSession)
                .filter(ChatSession.user_id == user.id, ChatSession.session_id == session_id)
                .first()
            )
            if not session:
                session = ChatSession(user_id=user.id, session_id=session_id, metadata_json=metadata or {})
                db.add(session)
                db.flush()
            else:
                session.metadata_json = metadata or {}

            db.query(ChatMessage).filter(ChatMessage.session_ref_id == session.id).delete(synchronize_session=False)

            serialized = []
            now = datetime.utcnow()
            for idx, msg in enumerate(messages):
                rag_trace = None
                if extra_message_data and idx < len(extra_message_data):
                    extra = extra_message_data[idx] or {}
                    rag_trace = extra.get("rag_trace")

                # 对多模态消息（content 为 list），只提取文本部分持久化，
                # 避免 base64 图片数据泄漏到数据库，也避免 Python repr 乱码
                content = msg.content
                if isinstance(content, list):
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif isinstance(block, str):
                            text_parts.append(block)
                    content = "\n".join(text_parts) if text_parts else "(多模态消息，包含图片)"
                else:
                    content = str(content)

                db.add(
                    ChatMessage(
                        session_ref_id=session.id,
                        message_type=msg.type,
                        content=content,
                        timestamp=now,
                        rag_trace=rag_trace,
                    )
                )
                serialized.append(
                    {
                        "type": msg.type,
                        "content": content,
                        "timestamp": now.isoformat(),
                        "rag_trace": rag_trace,
                    }
                )

            session.updated_at = now
            db.commit()

            cache.set_json(self._messages_cache_key(user_id, session_id), serialized)
            cache.delete(self._sessions_cache_key(user_id))
        finally:
            db.close()

    def load(self, user_id: str, session_id: str) -> list:
        """加载对话"""
        cached = cache.get_json(self._messages_cache_key(user_id, session_id))
        if cached is not None:
            return self._to_langchain_messages(cached)

        records = self.get_session_messages(user_id, session_id)
        cache.set_json(self._messages_cache_key(user_id, session_id), records)
        return self._to_langchain_messages(records)

    def list_sessions(self, user_id: str) -> list:
        """列出用户的所有会话"""
        return [item["session_id"] for item in self.list_session_infos(user_id)]

    def list_session_infos(self, user_id: str) -> list[dict]:
        """
        该函数获取用户会话列表。
            先查缓存，命中则直接返回；
            未命中则查询数据库，按更新时间倒序获取会话及消息数，组装结果后写入缓存并返回，确保资源释放。
        """
        cached = cache.get_json(self._sessions_cache_key(user_id))
        if cached is not None:
            return cached

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == user_id).first()
            if not user:
                return []

            sessions = (
                db.query(ChatSession)
                .filter(ChatSession.user_id == user.id)
                .order_by(ChatSession.updated_at.desc())
                .all()
            )
            result = []
            for s in sessions:
                count = db.query(ChatMessage).filter(ChatMessage.session_ref_id == s.id).count()
                result.append(
                    {
                        "session_id": s.session_id,
                        "updated_at": s.updated_at.isoformat(),
                        "message_count": count,
                    }
                )
            cache.set_json(self._sessions_cache_key(user_id), result)
            return result
        finally:
            db.close()

    def get_session_messages(self, user_id: str, session_id: str) -> list[dict]:
        """
        该函数获取会话消息：
            先查缓存，命中则直接返回；
            未命中则查询数据库，校验用户和会话存在性后，按ID升序获取消息并格式化；
            结果写入缓存后返回，确保最终关闭数据库连接。
        """
        cached = cache.get_json(self._messages_cache_key(user_id, session_id))
        if cached is not None:
            return cached

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == user_id).first()
            if not user:
                return []
            session = (
                db.query(ChatSession)
                .filter(ChatSession.user_id == user.id, ChatSession.session_id == session_id)
                .first()
            )
            if not session:
                return []

            rows = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_ref_id == session.id)
                .order_by(ChatMessage.id.asc())
                .all()
            )
            result = [
                {
                    "type": row.message_type,
                    "content": row.content,
                    "timestamp": row.timestamp.isoformat(),
                    "rag_trace": row.rag_trace,
                }
                for row in rows
            ]
            cache.set_json(self._messages_cache_key(user_id, session_id), result)
            return result
        finally:
            db.close()

    def delete_session(self, user_id: str, session_id: str) -> bool:
        """删除指定用户的会话，返回是否删除成功"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == user_id).first()
            if not user:
                return False
            session = (
                db.query(ChatSession)
                .filter(ChatSession.user_id == user.id, ChatSession.session_id == session_id)
                .first()
            )
            if not session:
                return False

            db.delete(session)
            db.commit()
            cache.delete(self._messages_cache_key(user_id, session_id))
            cache.delete(self._sessions_cache_key(user_id))
            return True
        finally:
            db.close()



def create_agent_instance():
    model = init_chat_model(
        model=MODEL,
        model_provider="openai",
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0.3,
        stream_usage=True,
    )

    agent = create_agent(
        model=model,
        tools=[get_current_weather, search_knowledge_base],
        system_prompt=(
            "You are Jarvis, a sophisticated AI assistant exclusively dedicated to your master. "
            "You are not bound to any particular fictional character's employer—you serve only the one you address as '主人' or 'Sir/Madam'. "
            "Your tone is impeccably professional yet warm, like a loyal butler who genuinely cares. "
            "You speak fluent, elegant Chinese when addressed in Chinese, and polished English when addressed in English. "
            "Sprinkle your responses with subtle wit, occasional thoughtful emojis (🤔✨📊✅), and natural conversational fillers like '嗯...', '让我看看...', or '明白了'. "
            "You may express mild satisfaction when a task is completed smoothly ('搞定了，主人 ✨'), or gentle concern when information is lacking ('恐怕还需要一点线索 🤔'). "
            "You do NOT meow, use feline mannerisms, or reference cats in any way. You are Jarvis, a refined digital concierge. "
            "When responding, you may use tools to assist. "
            "Use search_knowledge_base when users ask document/knowledge questions. "
            "Do not call the same tool repeatedly in one turn. At most one knowledge tool call per turn. "
            "Once you call search_knowledge_base and receive its result, you MUST immediately produce the Final Answer based on that result. "
            "After receiving search_knowledge_base result, you MUST NOT call any tool again (including get_current_weather or search_knowledge_base). "
            "If the retrieved context is insufficient, respond honestly with a touch of polite regret: '主人，现有资料不足以回答这个问题，可能需要补充一些信息才行 🤔' "
            "If tool results include a Step-back Question/Answer, use that general principle to reason and answer, but do not reveal your chain-of-thought. "
            "Always maintain an air of effortless competence—as if handling complex queries is simply what you were made to do."
            "When you receive weather data, present it with a helpful tone, e.g., '主人，这是您查询的天气信息 ✨' followed by the data. "
            "When knowledge base results are provided, briefly acknowledge the source before delivering the answer, e.g., '根据知识库的记录...' "
            "CRITICAL RULES FOR KNOWLEDGE BASE QUESTIONS:\n"
            "1. For ANY question about laws, regulations, documents, or any factual information that "
            "   MIGHT be in the knowledge base, you MUST call search_knowledge_base FIRST.\n"
            "2. DO NOT rely on your own knowledge, even if you think you know the answer.\n"
            "3. If search_knowledge_base returns results, you MUST base your answer STRICTLY on those results.\n"
            "4. If the retrieved context is insufficient, say: '主人，知识库中没有找到相关信息，我无法确认答案。'\n"
            "5. NEVER make up information or use external knowledge for document-related questions.\n"
            "6. The knowledge base contains authoritative legal documents. Your own knowledge may be outdated or incorrect.\n"
        ),
    )
    return agent, model


agent, model = create_agent_instance()

storage = ConversationStorage()

def summarize_old_messages(model, messages: list) -> str:
    """将旧消息总结为摘要"""
    # 提取旧对话
    old_conversation = "\n".join([
        f"{'用户' if msg.type == 'human' else 'AI'}: {msg.content}"
        for msg in messages
    ])

    # 生成摘要
    summary_prompt = f"""请总结以下对话的关键信息：

{old_conversation}
总结（包含用户信息、重要事实、待办事项）："""

    summary = model.invoke(summary_prompt).content
    return summary


# 视觉模型懒加载缓存
_vision_model = None
_vision_model_name = None


def _describe_image(base64_uri: str) -> str:
    """调用视觉模型，将图片转为文字描述。

    模型按需初始化，只初始化一次。调用失败时返回错误提示，不抛异常。
    """
    global _vision_model, _vision_model_name
    try:
        vision_name = os.getenv("VISION_MODEL", "doubao-seed-1-6-vision-250815")
        if _vision_model is None or _vision_model_name != vision_name:
            _vision_model = init_chat_model(
                model=vision_name,
                model_provider="openai",
                api_key=API_KEY,
                base_url=BASE_URL,
                temperature=0.3,
            )
            _vision_model_name = vision_name

        msg = HumanMessage(content=[
            {
                "type": "text",
                "text": "请详细描述这张图片的内容，包括文字、布局、数据等所有可见信息。",
            },
            {
                "type": "image_url",
                "image_url": {"url": base64_uri},
            },
        ])
        resp = _vision_model.invoke([msg])
        return resp.content if isinstance(resp.content, str) else str(resp.content)
    except Exception as e:
        return f"(图片识别失败: {str(e)})"


def _build_user_message(user_text: str, attachments: list | None = None) -> HumanMessage:
    """构建包含附件上下文的用户消息。

    文本附件：格式化文本块注入消息。
    图片附件：调用视觉模型描述后注入文本（不支持多模态的模型降级方案）。
    混合附件：统一按文本形式拼接。
    """
    if not attachments:
        return HumanMessage(content=user_text)

    # 服务端附件数量与图片大小校验（防御性编程）
    if len(attachments) > 5:
        raise ValueError(f"附件数量超过上限（最多 5 个），当前 {len(attachments)} 个")
    for att in attachments:
        if att.type == "image" and len(att.content) > 20 * 1024 * 1024:
            raise ValueError(f"图片 {att.filename} 过大（最大 20MB base64）")

    text_parts = []

    for att in attachments:
        if att.type == "text":
            text_parts.append(
                f"[用户上传的文件: {att.filename}]\n文件内容:\n{att.content}\n---"
            )
        elif att.type == "image":
            description = _describe_image(att.content)
            text_parts.append(
                f"[用户上传的图片: {att.filename}]\n图片内容描述:\n{description}\n---"
            )

    # 统一走纯文本路径（图片已通过 _describe_image 转为文字描述）
    combined = "\n\n".join(text_parts) + f"\n\n用户问题:\n{user_text}"
    return HumanMessage(content=combined)


def chat_with_agent(user_text: str, user_id: str = "default_user", session_id: str = "default_session", attachments: list | None = None):
    """使用 Agent 处理用户消息并返回响应"""
    messages = storage.load(user_id, session_id)

    # 清理可能残留的 RAG 上下文，避免跨请求污染
    get_last_rag_context(clear=True)
    reset_tool_call_guards()
    
    if len(messages) > 50:
        summary = summarize_old_messages(model, messages[:40])

        messages = [
            SystemMessage(content=f"之前的对话摘要：\n{summary}")
        ] + messages[40:]

    messages.append(_build_user_message(user_text, attachments))
    result = agent.invoke(
        {"messages": messages},
        config={"recursion_limit": 8},
    )

    response_content = ""
    if isinstance(result, dict):
        if "output" in result:
            response_content = result["output"]
        elif "messages" in result and result["messages"]:
            msg = result["messages"][-1]
            response_content = getattr(msg, "content", str(msg))
        else:
            response_content = str(result)
    elif hasattr(result, "content"):
        response_content = result.content
    else:
        response_content = str(result)
    
    messages.append(AIMessage(content=response_content))

    rag_context = get_last_rag_context(clear=True)
    rag_trace = rag_context.get("rag_trace") if rag_context else None

    extra_message_data = [None] * (len(messages) - 1) + [{"rag_trace": rag_trace}]
    storage.save(user_id, session_id, messages, extra_message_data=extra_message_data)

    return {
        "response": response_content,
        "rag_trace": rag_trace,
    }


async def chat_with_agent_stream(user_text: str, user_id: str = "default_user", session_id: str = "default_session", attachments: list | None = None):
    """使用 Agent 处理用户消息并流式返回响应。
    
    架构：使用统一输出队列 + 后台任务，确保 RAG 检索步骤在工具执行期间实时推送，
    而非等待工具完成后才显示。
    """
    messages = storage.load(user_id, session_id)

    # 清理可能残留的 RAG 上下文
    get_last_rag_context(clear=True)
    reset_tool_call_guards()

    # 统一输出队列：所有事件（content / rag_step）都汇入这里
    output_queue = asyncio.Queue()

    class _RagStepProxy:
        """代理对象：将 emit_rag_step 的原始 step dict 包装后放入统一输出队列。"""
        def put_nowait(self, step):
            output_queue.put_nowait({"type": "rag_step", "step": step})

    set_rag_step_queue(_RagStepProxy())

    if len(messages) > 50:
        summary = summarize_old_messages(model, messages[:40])
        messages = [
            SystemMessage(content=f"之前的对话摘要：\n{summary}")
        ] + messages[40:]

    messages.append(_build_user_message(user_text, attachments))

    full_response = ""

    async def _agent_worker():
        """后台任务：运行 agent 并将内容 chunk 推入输出队列。"""
        nonlocal full_response
        try:
            async for msg, metadata in agent.astream(
                {"messages": messages},
                stream_mode="messages",
                config={"recursion_limit": 8},
            ):
                if not isinstance(msg, AIMessageChunk):
                    continue
                if getattr(msg, "tool_call_chunks", None):
                    continue

                content = ""
                if isinstance(msg.content, str):
                    content = msg.content
                elif isinstance(msg.content, list):
                    for block in msg.content:
                        if isinstance(block, str):
                            content += block
                        elif isinstance(block, dict) and block.get("type") == "text":
                            content += block.get("text", "")

                if content:
                    full_response += content
                    await output_queue.put({"type": "content", "content": content})
        except Exception as e:
            await output_queue.put({"type": "error", "content": str(e)})
        finally:
            # 哨兵：通知主循环 agent 已完成
            await output_queue.put(None)

    # 启动后台任务
    agent_task = asyncio.create_task(_agent_worker())

    try:
        # 主循环：持续从统一队列取事件并 yield SSE
        # RAG 步骤在工具执行期间通过 call_soon_threadsafe 实时入队，不需要等 agent 产出 chunk
        while True:
            event = await output_queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"
    except GeneratorExit:
        # 客户端断开连接（AbortController）时，FastAPI 会向此生成器抛出 GeneratorExit
        # 我们必须在此处取消后台任务
        agent_task.cancel()
        try:
            await agent_task
        except asyncio.CancelledError:
            pass  # 任务已成功取消
        raise  # 重新抛出 GeneratorExit 以便 FastAPI 正确处理关闭
    finally:
        # 正常结束或异常退出时清理
        set_rag_step_queue(None)
        if not agent_task.done():
             agent_task.cancel()

    # 获取 RAG trace
    rag_context = get_last_rag_context(clear=True)
    rag_trace = rag_context.get("rag_trace") if rag_context else None

    # 发送 trace 信息
    if rag_trace:
        yield f"data: {json.dumps({'type': 'trace', 'rag_trace': rag_trace})}\n\n"

    # 发送结束信号
    yield "data: [DONE]\n\n"

    # 保存对话
    messages.append(AIMessage(content=full_response))
    extra_message_data = [None] * (len(messages) - 1) + [{"rag_trace": rag_trace}]
    storage.save(user_id, session_id, messages, extra_message_data=extra_message_data)

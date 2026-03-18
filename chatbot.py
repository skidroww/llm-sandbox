import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from dotenv import load_dotenv
load_dotenv()
import uuid


REDIS_URL = "redis://default:123@localhost:6379/0"


def get_message_history(sesssion_id : str) -> RedisChatMessageHistory:
    return RedisChatMessageHistory(sesssion_id, REDIS_URL)


def main():
    model = ChatOpenAI(model = "gpt-4.1-mini-2025-04-14", temperature=0.8)


    if 'session_id' not in st.session_state:
        # st.session_state.session_id = str(uuid.uuid4())
        st.session_state.session_id = 'skn25_13'


    prompt = ChatPromptTemplate( [
        ("system", "당신은 초등학교 동창입니다. 사이가 좋지 않은 관계입니다."),
        MessagesPlaceholder(variable_name='history'),
        ('human' , "{question}")]
    )


    chain = prompt | model


    chain_with_message = RunnableWithMessageHistory(
        chain,
        get_message_history,
        input_messages_key='question',
        history_messages_key='history')


    history = get_message_history(st.session_state.session_id)
    messages = history.messages
    for msg in messages:
        role = 'user' if msg.type == 'human' else 'assistant'
        st.chat_message(role).write(msg.content)






    if user_input := st.chat_input("대화를 입력하세요"):
        st.chat_message('user').write(user_input)
        with st.chat_message('assistant'):
            resp = chain_with_message.invoke({'question' : user_input}, config=
                                    {'configurable' : {'session_id' : st.session_state.session_id}})
            st.write(resp.content)






if __name__ == "__main__":
    main()

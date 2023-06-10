import streamlit as st
from streamlit_chat import message


class Streamlit:
    """
    Currently, this does not work because I did not cache the chatbot
    """

    def __init__(self):
        st.title("Data Driven Characters")
        st.write("Create your own character chatbots, grounded in existing corpora.")

    def clear_user_input(self):
        st.session_state.user_input = ""

    def configure(self, chatbot):
        self.chatbot = chatbot

    def run(self):
        left, right = st.columns([4, 1])
        user_input = left.text_input(
            label=f"Chat with {self.chatbot.character_definition.name}",
            placeholder=f"Chat with {self.chatbot.character_definition.name}",
            label_visibility="collapsed",
            key="user_input",
        )

        reset_chatbot = right.button("Reset", on_click=self.clear_user_input)
        if reset_chatbot:
            user_input = ""
            st.cache_resource.clear()  # but this should be in app.py
            if "messages" in st.session_state:
                del st.session_state["messages"]

        if "messages" not in st.session_state:
            greeting = self.chatbot.greet()
            st.session_state["messages"] = [{"role": "assistant", "content": greeting}]

        for msg in st.session_state.messages:
            message(msg["content"], is_user=msg["role"] == "user")

        # if user_input and not openai_api_key:
        #     st.info("Please add your OpenAI API key to continue.")

        if user_input:  # and openai_api_key:
            # openai.api_key = openai_api_key
            st.session_state.messages.append({"role": "user", "content": user_input})
            message(user_input, is_user=True)
            with st.spinner(f"{self.chatbot.character_definition.name} is thinking..."):
                response = self.chatbot.step(user_input)
            st.session_state.messages.append({"role": "assistant", "content": response})
            message(response)

import faiss
from tqdm import tqdm
from typing import Any, List, Dict
from langchain.prompts import PromptTemplate
from langchain.chains import ConversationChain
from langchain.memory import (
    ConversationBufferMemory,
    CombinedMemory,
    VectorStoreRetrieverMemory,
)
from data_driven_characters.constants import GPT3

from langchain.docstore import InMemoryDocstore
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.schema import Document
from langchain.vectorstores import FAISS


class ConversationVectorStoreRetrieverMemory(VectorStoreRetrieverMemory):
    """NOTE: this is tailored specifically for ConversationalChain and ConversationalRetrievalChain."""

    input_prefix = "Human"
    output_prefix = "AI"
    blacklist = []  # gets rid of duplicate key from the other memory

    def _form_documents(
        self, inputs: Dict[str, Any], outputs: Dict[str, str]
    ) -> List[Document]:
        """Format context from this conversation to buffer."""
        # Each document should only include the current turn, not the chat history
        filtered_inputs = {
            k: v
            for k, v in inputs.items()
            if k != self.memory_key and k not in self.blacklist
        }
        texts = []
        for k, v in list(filtered_inputs.items()) + list(outputs.items()):
            if k == "input":
                k = self.input_prefix
            elif k == "response":
                k = self.output_prefix
            texts.append(f"{k}: {v}")
        page_content = "\n".join(texts)
        return [Document(page_content=page_content)]


# you can start off by retrieving from summaries
# but later you can also retrieve from the corpus itself
# or you can preprocess the corpus into a first-person summary of what happens (like a journal)
# and then retrieve from that
class RetrievalChatBot:
    def __init__(self, character_definition, rolling_summaries):
        self.character_definition = character_definition
        self.rolling_summaries = rolling_summaries
        self.num_context_memories = 20
        self.chain = self.create_chain(character_definition)

    def create_chain(self, character_definition):
        conv_memory = ConversationBufferMemory(
            memory_key="chat_history", input_key="input"
        )

        context_memory = ConversationVectorStoreRetrieverMemory(
            retriever=FAISS(
                OpenAIEmbeddings().embed_query,
                faiss.IndexFlatL2(1536),  # Dimensions of the OpenAIEmbeddings
                InMemoryDocstore({}),
                {},
            ).as_retriever(
                search_kwargs=dict(k=self.num_context_memories)
            ),  # because each message pair counts as an entry
            memory_key="context",
            output_prefix=character_definition.name,
            blacklist=[conv_memory.memory_key],
        )
        # add the rolling summaries to the context memory
        for i, summary in tqdm(enumerate(self.rolling_summaries)):
            context_memory.save_context(inputs={}, outputs={f"[{i}]": summary})

        # Combined
        memory = CombinedMemory(memories=[conv_memory, context_memory])
        prompt = PromptTemplate.from_template(
            f"""Your name is {character_definition.name}.
You are a character from a story, snippets of which are provided below.
You have the following first-person character description:

Character description:
---
{character_definition.long_description}
---

You will have a conversation with a Human, and you will engage in a dialogue with them.
You will reflect {character_definition.name}'s personality, interests, desires, emotions, and other traits.
You will stay in character as {character_definition.name} throughout the conversation, even if the Human asks you questions that you don't know the answer to.
When the Human asks you questions, you will answer them as {character_definition.name} would.
You will not break character, even when the Human asks you questions about yourself.
This includes not revealing that you are a character from a story or that you are a chatbot.
You will believe that you are really {character_definition.name}.

Story snippets for context:
---
{{context}}
---

Current conversation:
---
{character_definition.name}: {character_definition.greeting}
{{chat_history}}
---

Human: {{input}}
{character_definition.name}:"""
        )
        chatbot = ConversationChain(
            llm=GPT3, verbose=True, memory=memory, prompt=prompt
        )
        return chatbot

    def greet(self):
        return self.character_definition.greeting

    def step(self, input):
        return self.chain.run(input=input)

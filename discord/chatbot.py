from openai import OpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.agents import OpenAIFunctionsAgent, AgentExecutor
from langchain.agents.openai_functions_agent.agent_token_buffer_memory import (
    AgentTokenBufferMemory, )
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, AIMessage, HumanMessage
from langchain.prompts import MessagesPlaceholder
from langchain.agents import AgentExecutor
from langchain.llms import OpenAI
from langchain.prompts.prompt import PromptTemplate
from langchain.chains import ConversationChain
from langchain.llms import OpenAI
import os
from langchain.vectorstores import Pinecone
from templates import template
from langchain.chains import RetrievalQA
from langchain.memory import ConversationBufferMemory
from mongodb import get_chat_history, set_chat_history

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
import pinecone

client = OpenAI(
    # This is the default and can be omitted
    api_key=OPENAI_API_KEY, )

pinecone.init(api_key="57e84506-df9f-4d70-81e3-484ecfd91cff",
              environment="gcp-starter")
index_name = "demo"


def ai_responses(query, user_phone, history=None):
  if history is None:
    history = {"messages": []}

  msg = []

  # Process history messages
  try:
    history_records = get_chat_history(user_phone)
    if history_records and "messages" in history_records:
      for message_data in history_records["messages"]:
        role = message_data['role']
        content = message_data['content']
        if role == 'assistant':
          msg.append(AIMessage(content=content))
        elif role == 'user':
          msg.append(HumanMessage(content=content))
    else:
      starter_message = "Your AI Assistant, feel free to share anything."
      msg.append(AIMessage(content=starter_message))
      history["messages"].append({
          'role': 'assistant',
          'content': starter_message
      })
  except Exception as e:
    # Initialize history if get_history returns None
    history = {"messages": []}
    starter_message = "Your AI therapist, feel free to share anything."
    msg.append(AIMessage(content=starter_message))
    history["messages"].append({
        'role': 'assistant',
        'content': starter_message
    })
    print(f"Error in getting chat history: {e}")

  msg.append(HumanMessage(content=query))
  history["messages"].append({'role': 'user', 'content': query})

  embeddings = OpenAIEmbeddings()
  docsearch = Pinecone.from_existing_index(index_name, embeddings)

  prompt_template = template() + """
    {context}
    User: {question}
    AI Assistant:
    """
  memory = ConversationBufferMemory()
  for i in range(len(history["messages"]) - 1):
    if history["messages"][i]['role'] == 'user' and history["messages"][
        i + 1]['role'] == 'assistant':
      memory.save_context({"query": history["messages"][i]['content']},
                          {"result": history["messages"][i + 1]['content']})

  PROMPT = PromptTemplate(input_variables=["context", "question"],
                          template=prompt_template)
  qa_with_sources = RetrievalQA.from_chain_type(
      llm=ChatOpenAI(model_name="gpt-4-1106-preview", temperature=0.2),
      chain_type="stuff",
      verbose=False,
      chain_type_kwargs={
          "verbose": False,
          "prompt": PROMPT,
      },
      retriever=docsearch.as_retriever(search_kwargs={'k': 7},
                                       include_metadata=True),
      return_source_documents=False,
      memory=memory)
  response = qa_with_sources.run({'query': query})

  history["messages"].append({
      'role': 'assistant',
      'content': response
  })

  # Update the user's history in the database
  va = set_chat_history(user_phone, history["messages"])

  return response

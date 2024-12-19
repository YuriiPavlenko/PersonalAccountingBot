from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate

class ExpenseTrackingAgent:
    def __init__(self, sheets_client):
        self.llm = ChatOpenAI()
        self.sheets_client = sheets_client
        
        system_prompt = """You are a helpful assistant that helps families track their expenses.
        Help them categorize expenses and maintain their budget."""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{input}"),
            ("assistant", "{agent_scratchpad}")  # Добавляем agent_scratchpad
        ])
        
        # Определяем инструменты как список объектов
        tools = [
            {
                "func": self.sheets_client.append_expense,
                "description": "Добавляет расход в таблицу",
                "name": "append_expense"
            }
        ]
        
        self.agent = create_openai_functions_agent(
            llm=self.llm,
            prompt=prompt,
            tools=tools
        )
        
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=tools,
            verbose=True
        )

    async def process_message(self, message):
        return await self.agent_executor.arun(message)

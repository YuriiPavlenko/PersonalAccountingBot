from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate
from langchain.tools import StructuredTool

class AppendExpenseSchema(BaseModel):
    date: str
    description: str
    amount: float
    currency: str
    cash: bool
    user: str

class ExpenseTrackingAgent:
    def __init__(self, sheets_client):
        self.llm = ChatOpenAI()
        self.sheets_client = sheets_client
        
        system_prompt = """You are a helpful assistant that helps families track their expenses.
        Help them categorize expenses and maintain their budget."""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{input}"),
            ("assistant", "{agent_scratchpad}")
        ])
        
        # Создаем инструмент с помощью StructuredTool
        append_expense_tool = StructuredTool(
            name="append_expense",
            description="Добавляет расход в таблицу",
            func=self.sheets_client.append_expense,
            args_schema=AppendExpenseSchema
        )
        
        tools = [append_expense_tool]
        
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

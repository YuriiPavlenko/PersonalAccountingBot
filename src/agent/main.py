import logging
from datetime import datetime
import pytz
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
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing ChatOpenAI...")
        self.llm = ChatOpenAI()
        
        self.logger.info("Setting up SheetsClient...")
        self.sheets_client = sheets_client
        
        system_prompt = """You are a helpful assistant that helps a family to track their expenses.
        Help them categorize expenses and maintain their budget."""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{input}"),
            ("assistant", "{agent_scratchpad}")
        ])
        
        self.logger.info("Creating append_expense tool...")
        append_expense_tool = StructuredTool(
            name="append_expense",
            description="Adds an expense to the sheet",
            func=self.sheets_client.append_expense,
            args_schema=AppendExpenseSchema
        )
        
        self.logger.info("Creating get_current_time tool...")
        get_current_time_tool = StructuredTool(
            name="get_current_time",
            description="Returns the current time in the Thailand timezone",
            func=self.get_current_time,
            args_schema=None  # No arguments needed
        )
        
        tools = [append_expense_tool, get_current_time_tool]
        
        self.logger.info("Creating OpenAI functions agent...")
        self.agent = create_openai_functions_agent(
            llm=self.llm,
            prompt=prompt,
            tools=tools
        )
        
        self.logger.info("Creating AgentExecutor...")
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=tools,
            input_keys=["input"],  # Specify the input key
            output_keys=["output"],  # Specify the output key
            verbose=True
        )

    async def process_message(self, message):
        self.logger.info(f"Processing message: {message}")
        return await self.agent_executor.ainvoke({"input": message})

    def get_current_time(self):
        tz = pytz.timezone('Asia/Bangkok')
        return datetime.now(tz).isoformat()

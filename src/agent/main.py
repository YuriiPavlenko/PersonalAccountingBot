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
        
        system_prompt = """You are a helpful assistant that reads and writes to a google sheets table.
        For each expense entry, you should:
        1. Extract the expense information
        2. Format it for confirmation
        3. Wait for user approval before writing to the sheet
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{input}"),
            ("assistant", "{agent_scratchpad}")
        ])
        
        # Create a sync version of append_expense for the agent to use
        def sync_append_expense(*args, **kwargs):
            # Instead of actually appending, just return the formatted data
            return {
                "date": kwargs.get('date'),
                "description": kwargs.get('description'),
                "amount": kwargs.get('amount'),
                "currency": kwargs.get('currency'),
                "cash": kwargs.get('cash', False),
                "user": kwargs.get('user', 'default_user')
            }
        
        self.logger.info("Creating append_expense tool...")
        append_expense_tool = StructuredTool(
            name="append_expense",
            description="Formats an expense entry for confirmation",
            func=sync_append_expense,
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
        self.logger.info(f"Processing new message: {message}")
        try:
            result = await self.agent_executor.ainvoke({"input": message})
            self.logger.info(f"Agent processed message successfully: {result}")
            
            if result and "output" in result:
                # Format the data for confirmation
                expense_data = result["output"]
                summary = self.format_expense_summary(expense_data)
                return {
                    "data": expense_data,
                    "summary": summary
                }
            else:
                self.logger.warning("Agent returned no result")
                return None
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            raise

    async def process_correction(self, previous_expense, correction):
        self.logger.info(f"Processing correction. Previous expense: {previous_expense}")
        self.logger.info(f"Correction text: {correction}")
        
        try:
            result = await self.agent_executor.ainvoke({
                "input": f"Previous expense: {previous_expense['summary']}\nCorrection: {correction}"
            })
            self.logger.info(f"Agent processed correction successfully: {result}")
            
            if result and "output" in result:
                # Use the LLM's output directly
                expense_data = result["output"]
                summary = self.format_expense_summary(expense_data)
                self.logger.info(f"Formatted corrected expense summary: {summary}")
                return {
                    "data": expense_data,
                    "summary": summary
                }
            else:
                self.logger.warning("Agent returned no result for correction")
                return None
        except Exception as e:
            self.logger.error(f"Error processing correction: {str(e)}")
            raise

    async def write_expense(self, expense_data):
        """Actually write the expense to the sheet after confirmation"""
        self.logger.info(f"Writing expense to sheet: {expense_data}")
        try:
            await self.sheets_client.append_expense(**expense_data["data"])
            self.logger.info("Successfully wrote expense to sheet")
        except Exception as e:
            self.logger.error(f"Failed to write expense to sheet: {str(e)}")
            raise

    def parse_expense_data(self, output):
        """Parse the LLM output to extract expense data."""
        self.logger.info(f"Parsing expense data from output: {output}")
        
        # Initialize default values
        expense_data = {
            "date": None,
            "description": None,
            "amount": None,
            "currency": None,
            "cash": None,
            "user": None
        }
        
        try:
            # Split output into lines and process each line
            lines = output.lower().split('\n')
            for line in lines:
                if 'date:' in line:
                    expense_data['date'] = line.split('date:')[-1].strip()
                elif 'amount:' in line:
                    amount_str = line.split('amount:')[-1].strip()
                    # Extract numeric amount and currency
                    parts = amount_str.split()
                    if len(parts) >= 1:
                        expense_data['amount'] = float(parts[0].replace(',', ''))
                    if len(parts) >= 2:
                        expense_data['currency'] = parts[1].upper()
                elif 'description:' in line:
                    expense_data['description'] = line.split('description:')[-1].strip()
                elif 'payment:' in line or 'paid by:' in line:
                    expense_data['cash'] = 'cash' in line.lower()
                elif 'user:' in line:
                    expense_data['user'] = line.split('user:')[-1].strip()

            # Validate all required fields are present
            if None in expense_data.values():
                missing = [k for k, v in expense_data.items() if v is None]
                raise ValueError(f"Missing required fields: {missing}")

            return expense_data

        except Exception as e:
            self.logger.error(f"Error parsing expense data: {str(e)}")
            raise ValueError(f"Failed to parse expense data: {str(e)}")

    def format_expense_summary(self, expense_data):
        return f"""
📅 Date: {expense_data['date']}
💰 Amount: {expense_data['amount']} {expense_data['currency']}
📝 Description: {expense_data['description']}
💳 Payment: {'Cash' if expense_data['cash'] else 'Card'}
👤 User: {expense_data['user']}
"""

    def get_current_time(self):
        self.logger.info(f"Agent fetches current time.")
        tz = pytz.timezone('Asia/Bangkok')
        return datetime.now(tz).isoformat()

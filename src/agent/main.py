import logging
import pytz
import os
from datetime import datetime
from typing import TypeVar, List, Union, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langchain.tools import StructuredTool
from langchain.prompts import ChatPromptTemplate
from langsmith import Client
from langchain_core.tracers import LangChainTracer
from src.schemas import ExpenseSchema
from pydantic import BaseModel
from typing_extensions import Annotated

# Define state types
S = TypeVar("S", bound=Dict[str, Any])

class GetTimeToolSchema(BaseModel):
    """Schema for get_current_time tool that takes no arguments"""
    pass

# Define state schema
class ExpenseState(BaseModel):
    message: str
    expense_data: Optional[Dict[str, Any]] = None
    formatted_expense: Optional[str] = None
    status: Optional[str] = None

class ExpenseTrackingAgent:
    def __init__(self, sheets_client):
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("Initializing LangSmith...")
        self.langsmith_client = Client()
        self.tracer = LangChainTracer(project_name="expense_tracking")
        
        self.logger.info("Initializing ChatOpenAI...")
        self.llm = ChatOpenAI()
        
        self.logger.info("Setting up SheetsClient...")
        self.sheets_client = sheets_client
        
        self.logger.info("Creating tools...")
        self.tools = self._create_tools()
        
        self.logger.info("Creating workflow graph...")
        self.workflow = self._create_workflow()

    def _create_tools(self) -> List[StructuredTool]:
        """Create the agent's tools"""
        append_expense_tool = StructuredTool(
            name="append_expense_to_table",
            description="Formats an expense entry for confirmation",
            func=self._format_expense,
            args_schema=ExpenseSchema
        )
        
        get_time_tool = StructuredTool(
            name="get_current_time",
            description="Returns current time in Thailand timezone",
            func=self._get_current_time,
            args_schema=GetTimeToolSchema  # Add args_schema even though it takes no arguments
        )
        
        return [append_expense_tool, get_time_tool]

    def _create_workflow(self) -> StateGraph:
        """Create the workflow graph"""
        # Create the graph with proper state schema
        workflow = StateGraph(ExpenseState)

        # Add nodes
        workflow.add_node("parse_expense", self._parse_expense)
        workflow.add_node("format_for_confirmation", self._format_for_confirmation)
        workflow.add_node("await_confirmation", self._await_confirmation)
        workflow.add_node("write_to_sheet", self._write_to_sheet)

        # Add edges
        workflow.add_edge("parse_expense", "format_for_confirmation")
        workflow.add_edge("format_for_confirmation", "await_confirmation")
        workflow.add_edge("await_confirmation", "write_to_sheet")
        workflow.add_edge("write_to_sheet", END)

        # Set entry point
        workflow.set_entry_point("parse_expense")

        return workflow.compile()

    async def _parse_expense(self, state: ExpenseState) -> ExpenseState:
        """Parse expense information from user input"""
        self.logger.info("Parsing expense from user input")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Extract expense information from the user message and return a structured JSON object with these exact fields:
            - date (YYYY-MM-DD)
            - description (string)
            - amount (number)
            - currency (string, e.g. THB)
            - cash (boolean)
            - user (string)
            
            For dates mentioned relatively (like "yesterday" or "three days ago"), calculate the actual date.
            """),
            ("user", "{input}")
        ])
        
        # Create chain with tracing
        chain = prompt | self.llm
        
        try:
            # Execute the chain with callbacks
            result = await chain.ainvoke(
                {"input": state.message},
                config={
                    "callbacks": [self.tracer],
                    "metadata": {
                        "project": "expense_tracking",
                        "run_name": "parse_expense"
                    }
                }
            )
            self.logger.info(f"Successfully parsed expense data: {result}")
            return ExpenseState(
                message=state.message,
                expense_data=result,
                formatted_expense=state.formatted_expense,
                status=state.status
            )
        except Exception as e:
            self.logger.error(f"Failed to parse expense: {str(e)}")
            raise

    async def _format_for_confirmation(self, state: ExpenseState) -> ExpenseState:
        """Format expense for user confirmation"""
        formatted = f"""
📝 Expense Details:
📅 Date: {state.expense_data['date']}
💰 Amount: {state.expense_data['amount']} {state.expense_data['currency']}
📄 Description: {state.expense_data['description']}
💳 Payment Type: {'Cash' if state.expense_data['cash'] else 'Card'}
👤 User: {state.expense_data['user']}
"""
        return ExpenseState(
            message=state.message,
            expense_data=state.expense_data,
            formatted_expense=formatted,
            status=state.status
        )

    async def _await_confirmation(self, state: ExpenseState) -> ExpenseState:
        """Await user confirmation"""
        # This node doesn't do anything as confirmation is handled by the bot
        return state

    async def _write_to_sheet(self, state: ExpenseState) -> ExpenseState:
        """Write confirmed expense to sheet"""
        await self.sheets_client.append_expense(**state.expense_data)
        return ExpenseState(
            message=state.message,
            expense_data=state.expense_data,
            formatted_expense=state.formatted_expense,
            status="written"
        )

    def _format_expense(self, **kwargs) -> Dict[str, Any]:
        """Format expense data"""
        return kwargs

    def _get_current_time(self) -> str:
        """Get current time in Thailand timezone"""
        self.logger.info("Fetching current time")
        tz = pytz.timezone('Asia/Bangkok')
        return datetime.now(tz).isoformat()

    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process a new expense message"""
        self.logger.info(f"Processing message: {message}")
        try:
            result = await self.workflow.ainvoke({"message": message})
            self.logger.info(f"Workflow completed with result: {result}")
            return {
                "data": result["expense_data"],
                "summary": result["formatted_expense"]
            }
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            raise

    async def write_expense(self, expense_data: Dict[str, Any]) -> None:
        """Write a confirmed expense to the sheet"""
        self.logger.info(f"Writing expense to sheet: {expense_data}")
        try:
            await self.sheets_client.append_expense(**expense_data["data"])
            self.logger.info("Successfully wrote expense to sheet")
        except Exception as e:
            self.logger.error(f"Failed to write expense to sheet: {str(e)}")
            raise
